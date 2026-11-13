import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'

const GAP = 12, EXCESS_GAP = 70
const cssVar = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim() || '#888888'

function labelSprite(text, color, background) {
    const canvas = document.createElement('canvas'), ratio = 2
    const context = canvas.getContext('2d')
    context.font = `500 ${22 * ratio}px "Inter Variable", Inter, system-ui, sans-serif`
    const width = Math.ceil(context.measureText(text).width) + 20 * ratio, height = 34 * ratio
    canvas.width = width; canvas.height = height
    context.font = `500 ${22 * ratio}px "Inter Variable", Inter, system-ui, sans-serif`
    context.fillStyle = background; context.beginPath(); context.roundRect(0, 0, width, height, 8 * ratio); context.fill()
    context.fillStyle = color; context.textBaseline = 'middle'; context.textAlign = 'center'; context.fillText(text, width / 2, height / 2 + ratio)
    const texture = new THREE.CanvasTexture(canvas); texture.colorSpace = THREE.SRGBColorSpace
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, depthTest: false, transparent: true }))
    sprite.scale.set(width / height * 28, 28, 1); sprite.renderOrder = 10
    return sprite
}

function frame(sizeX, sizeZ, y, color) {
    const x = sizeX / 2, z = sizeZ / 2
    const points = [[-x, -z], [x, -z], [x, -z], [x, z], [x, z], [-x, z], [-x, z], [-x, -z]].map(([px, pz]) => new THREE.Vector3(px, y, pz))
    return new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(points), new THREE.LineBasicMaterial({ color }))
}

// Posición de cada pallet sobre el piso del camión; los que superan la capacidad quedan aparte.
export function truckLayout(count, capacity, rowsAcross, sizeX, sizeZ) {
    const limit = capacity > 0 ? capacity : count
    const columns = Math.max(1, Math.ceil(limit / rowsAcross)), stepX = sizeX + GAP, stepZ = sizeZ + GAP
    const depth = rowsAcross * stepZ - GAP
    const at = index => {
        const inside = index < limit, local = inside ? index : index - limit
        const column = Math.floor(local / rowsAcross), row = local % rowsAcross
        const startX = inside ? 0 : columns * stepX + EXCESS_GAP
        return { x: startX + column * stepX + sizeX / 2, z: -depth / 2 + row * stepZ + sizeZ / 2, inside }
    }
    const excessColumns = Math.ceil(Math.max(0, count - limit) / rowsAcross)
    return { at, columns, excessColumns, bedLength: columns * stepX - GAP, depth, stepX }
}

export default function TruckScene3D({ pallets, capacity, rowsAcross, sizeX, sizeZ, colors, selectedId, onSelect, resetSignal }) {
    const host = useRef(null), stage = useRef(null), selectRef = useRef(onSelect)
    selectRef.current = onSelect

    useEffect(() => {
        const element = host.current
        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
        element.appendChild(renderer.domElement)
        const scene = new THREE.Scene(), camera = new THREE.PerspectiveCamera(38, 1, 5, 12000)
        const controls = new OrbitControls(camera, renderer.domElement)
        controls.enableDamping = true; controls.maxPolarAngle = Math.PI / 2 - 0.03; controls.minDistance = 120; controls.maxDistance = 4000
        scene.add(new THREE.HemisphereLight(0xffffff, 0x8a94a6, 1.6))
        const sun = new THREE.DirectionalLight(0xffffff, 1.9); sun.position.set(400, 900, 600); scene.add(sun)
        const group = new THREE.Group(); scene.add(group)
        const state = { renderer, scene, camera, controls, group, pick: [], frameId: 0 }
        stage.current = state
        const resize = () => { const width = element.clientWidth, height = element.clientHeight; if (!width || !height) return; renderer.setSize(width, height, false); camera.aspect = width / height; camera.updateProjectionMatrix() }
        const observer = new ResizeObserver(resize); observer.observe(element); resize()
        const loop = () => { state.frameId = requestAnimationFrame(loop); controls.update(); renderer.render(scene, camera) }
        loop()
        let down = null
        const pointerDown = event => { down = [event.clientX, event.clientY] }
        const pointerUp = event => {
            if (!down || Math.hypot(event.clientX - down[0], event.clientY - down[1]) > 5) return
            const box = renderer.domElement.getBoundingClientRect()
            const pointer = new THREE.Vector2((event.clientX - box.left) / box.width * 2 - 1, -(event.clientY - box.top) / box.height * 2 + 1)
            const ray = new THREE.Raycaster(); ray.setFromCamera(pointer, camera)
            const hit = ray.intersectObjects(state.pick.map(entry => entry.mesh), false)[0]
            const entry = hit && state.pick.find(item => item.mesh === hit.object)
            selectRef.current?.(entry ? entry.ids[hit.instanceId] ?? null : null)
        }
        renderer.domElement.addEventListener('pointerdown', pointerDown)
        renderer.domElement.addEventListener('pointerup', pointerUp)
        return () => {
            cancelAnimationFrame(state.frameId); observer.disconnect(); controls.dispose()
            renderer.domElement.removeEventListener('pointerdown', pointerDown); renderer.domElement.removeEventListener('pointerup', pointerUp)
            renderer.dispose(); element.removeChild(renderer.domElement); stage.current = null
        }
    }, [])

    // Reconstruye el contenido cuando cambian los datos, la selección o el tema.
    useEffect(() => {
        const state = stage.current
        if (!state) return
        const build = () => {
            const { group } = state
            group.traverse(object => { object.geometry?.dispose?.(); if (object.material) { object.material.map?.dispose?.(); object.material.dispose?.() } })
            group.clear(); state.pick = []
            const surface = new THREE.Color(cssVar('--surface')), border = new THREE.Color(cssVar('--border')), text = cssVar('--text'), muted = new THREE.Color(cssVar('--text-muted'))
            const danger = new THREE.Color(cssVar('--danger')), brand = new THREE.Color(cssVar('--brand-fg'))
            const dark = document.documentElement.dataset.theme === 'dark'
            const layout = truckLayout(pallets.length, capacity, rowsAcross, sizeX, sizeZ)
            const floorColor = surface.clone().lerp(muted, dark ? 0.16 : 0.1)
            const slab = (x, length, color) => { const mesh = new THREE.Mesh(new THREE.BoxGeometry(length + 30, 6, layout.depth + 30), new THREE.MeshLambertMaterial({ color })); mesh.position.set(x + length / 2, -3, 0); group.add(mesh) }
            slab(0, layout.bedLength, floorColor)
            const cab = new THREE.Mesh(new THREE.BoxGeometry(110, 150, layout.depth + 30), new THREE.MeshLambertMaterial({ color: floorColor.clone().lerp(muted, 0.25), transparent: true, opacity: 0.55 }))
            cab.position.set(-85, 69, 0); group.add(cab)
            const cabLabel = labelSprite('Cabina', text, `#${surface.getHexString()}`); cabLabel.position.set(-85, 168, 0); group.add(cabLabel)
            if (layout.excessColumns) {
                const start = layout.columns * layout.stepX + EXCESS_GAP, length = layout.excessColumns * layout.stepX - GAP
                slab(start, length, surface.clone().lerp(danger, 0.22))
                const note = labelSprite('Sin lugar en el camión', `#${danger.getHexString()}`, `#${surface.getHexString()}`); note.position.set(start + length / 2, -30, layout.depth / 2 + 45); group.add(note)
            }
            const limit = capacity > 0 ? capacity : pallets.length
            for (let index = pallets.length; index < limit; index++) { const spot = layout.at(index); const empty = frame(sizeX, sizeZ, 0.6, border.clone().lerp(muted, 0.5)); empty.position.set(spot.x, 0, spot.z); group.add(empty) }

            const total = pallets.reduce((sum, pallet) => sum + pallet.stack.boxes.length, 0)
            const unit = new THREE.BoxGeometry(1, 1, 1)
            const boxMesh = new THREE.InstancedMesh(unit, new THREE.MeshLambertMaterial(), Math.max(1, total))
            const baseMesh = new THREE.InstancedMesh(unit, new THREE.MeshLambertMaterial(), Math.max(1, pallets.length))
            const matrix = new THREE.Matrix4(), position = new THREE.Vector3(), scale = new THREE.Vector3(), rotation = new THREE.Quaternion()
            const wood = new THREE.Color('#B08A5B'), boxIds = [], baseIds = []
            let cursor = 0
            pallets.forEach((pallet, index) => {
                const spot = layout.at(index), faded = selectedId && selectedId !== pallet.id
                const tint = color => faded ? color.clone().lerp(surface, 0.8) : color
                matrix.compose(position.set(spot.x, pallet.stack.baseCm / 2, spot.z), rotation, scale.set(sizeX, pallet.stack.baseCm, sizeZ))
                baseMesh.setMatrixAt(index, matrix); baseMesh.setColorAt(index, tint(wood)); baseIds.push(pallet.id)
                for (const box of faded ? [] : pallet.stack.boxes) {
                    matrix.compose(position.set(spot.x + box.x, box.y + box.h / 2, spot.z + box.z), rotation, scale.set(box.w, box.h - 0.8, box.d))
                    const color = new THREE.Color(colors.get(box.color) || '#94A3B8')
                    if (box.floor % 2 === 0) color.offsetHSL(0, 0, -0.045)
                    boxMesh.setMatrixAt(cursor, matrix); boxMesh.setColorAt(cursor, tint(color)); boxIds.push(pallet.id); cursor++
                }
                if (!faded && pallet.stack.missing.length && !pallet.stack.boxes.length) {
                    const ghost = new THREE.Mesh(new THREE.BoxGeometry(sizeX - 2, 60, sizeZ - 2), new THREE.MeshLambertMaterial({ color: muted, transparent: true, opacity: 0.25 }))
                    ghost.position.set(spot.x, pallet.stack.baseCm + 30, spot.z); group.add(ghost)
                }
                const exceeded = pallet.heightExceeded || pallet.weightExceeded || !spot.inside
                if (!faded && pallet.heightLimitCm != null && (pallet.heightExceeded || selectedId === pallet.id)) { const line = frame(sizeX + 6, sizeZ + 6, pallet.heightLimitCm, pallet.heightExceeded ? danger : muted); line.position.set(spot.x, 0, spot.z); group.add(line) }
                if (selectedId === pallet.id) { const outline = frame(sizeX + 8, sizeZ + 8, 0.8, brand); outline.position.set(spot.x, 0, spot.z); group.add(outline) }
                if (!faded) { const label = labelSprite(pallet.id, exceeded ? `#${danger.getHexString()}` : text, `#${surface.getHexString()}`); label.position.set(spot.x, Math.max(pallet.stack.topCm, pallet.heightExceeded ? pallet.heightLimitCm || 0 : 0) + 26, spot.z); group.add(label) }
            })
            boxMesh.count = cursor; boxMesh.instanceMatrix.needsUpdate = true; if (boxMesh.instanceColor) boxMesh.instanceColor.needsUpdate = true
            baseMesh.instanceMatrix.needsUpdate = true; if (baseMesh.instanceColor) baseMesh.instanceColor.needsUpdate = true
            group.add(boxMesh, baseMesh)
            state.pick = [{ mesh: boxMesh, ids: boxIds }, { mesh: baseMesh, ids: baseIds }]
            state.layout = layout
        }
        build()
        const observer = new MutationObserver(build)
        observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
        return () => observer.disconnect()
    }, [pallets, capacity, rowsAcross, sizeX, sizeZ, colors, selectedId])

    // Encuadre: todo el camión, o el pallet elegido.
    useEffect(() => {
        const state = stage.current
        if (!state?.layout) return
        const { camera, controls, layout } = state
        const index = pallets.findIndex(pallet => pallet.id === selectedId)
        if (index >= 0) {
            const spot = layout.at(index), height = pallets[index].stack.topCm
            controls.target.set(spot.x, height / 2, spot.z)
            camera.position.set(spot.x + 300, height / 2 + 210, spot.z + 380)
        } else {
            const end = layout.excessColumns ? layout.columns * layout.stepX + EXCESS_GAP + layout.excessColumns * layout.stepX : layout.bedLength
            const length = end + 140, centre = end / 2 - 70, tallest = Math.max(180, ...pallets.map(pallet => pallet.stack.topCm))
            const radius = Math.hypot(length, layout.depth + 60, tallest) / 2
            const fit = radius / Math.sin(THREE.MathUtils.degToRad(camera.fov / 2)) / Math.min(1, camera.aspect)
            const distance = fit * 0.84
            controls.target.set(centre, tallest * 0.3, 0)
            camera.position.set(centre + distance * 0.3, tallest * 0.3 + distance * 0.5, distance * 0.81)
        }
        controls.update()
    }, [selectedId, pallets, capacity, rowsAcross, sizeX, sizeZ, resetSignal])

    return <div ref={host} className="scene3d h-full w-full" role="img" aria-label="Vista 3D del camión con sus pallets" />
}
