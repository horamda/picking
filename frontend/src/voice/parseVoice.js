// Interpreta lo que dice el controlador en la pantalla de control por voz.
// Función pura: no depende del navegador, así se puede probar con node:test.

// Números hablados de 0 a 50 (cantidades típicas de una cancha).
export const NUMBER_WORDS = {
  cero: 0, uno: 1, un: 1, una: 1, dos: 2, tres: 3, cuatro: 4, cinco: 5, seis: 6, siete: 7, ocho: 8, nueve: 9,
  diez: 10, once: 11, doce: 12, trece: 13, catorce: 14, quince: 15, dieciseis: 16, diecisiete: 17,
  dieciocho: 18, diecinueve: 19, veinte: 20, veintiuno: 21, veintiun: 21, veintidos: 22, veintitres: 23,
  veinticuatro: 24, veinticinco: 25, veintiseis: 26, veintisiete: 27, veintiocho: 28, veintinueve: 29,
  treinta: 30, cuarenta: 40, cincuenta: 50,
}

const COMMANDS = {
  correcto: 'ok', ok: 'ok', bien: 'ok', confirmo: 'ok',
  faltante: 'shortage', falta: 'shortage',
  error: 'corrected', corregido: 'corrected', corregida: 'corrected',
  repetir: 'repeat', repite: 'repeat',
  siguiente: 'next', proximo: 'next',
  anterior: 'prev',
}

export const VOICE_VOCABULARY = [
  ...Object.keys(NUMBER_WORDS), ...Object.keys(COMMANDS),
  'bulto', 'bultos', 'unidad', 'unidades',
]

export function normalize(text) {
  return String(text || '')
    .toLowerCase()
    .normalize('NFD').replace(/[̀-ͯ]/g, '')
    .replace(/[.,;:!?¿¡]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

// Devuelve { action, bultos?, unidades? }. action = 'unknown' si no entendió.
export function parseVoice(text) {
  const words = normalize(text).split(' ').filter(Boolean)
  if (!words.length) return { action: 'unknown' }

  // Comandos de una sola palabra o frase corta tienen prioridad.
  const command = words.map(w => COMMANDS[w]).find(Boolean)
  if (command && !words.some(w => w in NUMBER_WORDS || /^\d+$/.test(w))) {
    return { action: command }
  }

  // Cantidades: "dos bultos tres unidades", "dos y tres", "2 3".
  const numbers = []
  words.forEach((w, i) => {
    const value = /^\d+$/.test(w) ? Number(w) : NUMBER_WORDS[w]
    if (value === undefined) return
    const next = words[i + 1]
    numbers.push({ value, label: next === 'bulto' || next === 'bultos' ? 'bultos'
      : next === 'unidad' || next === 'unidades' ? 'unidades' : null })
  })
  if (numbers.length) {
    const labeled = (name) => numbers.find(n => n.label === name)?.value
    let bultos = labeled('bultos')
    let unidades = labeled('unidades')
    if (bultos === undefined && unidades === undefined) {
      // Sin etiquetas: primer número = bultos, segundo = unidades.
      bultos = numbers[0].value
      unidades = numbers[1]?.value
    }
    return { action: 'quantities', bultos, unidades }
  }

  // Frases compuestas como "error corregido" ya quedaron cubiertas por COMMANDS.
  return { action: 'unknown' }
}
