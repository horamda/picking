export function voiceBackupCsv(items) {
    const cell = value => {
        let text = String(value ?? '')
        // CSV is for spreadsheet viewing; the JSON backup retains exact originals.
        if (/^[\s]*[=+@-]/.test(text) || /^[\t\r\n]/.test(text)) text = "'" + text
        return '"' + text.replaceAll('"', '""') + '"'
    }
    return '\uFEFF' + [['Codigo', 'Descripcion para voz'], ...items.map(i => [i.sku, i.descripcion_voz])].map(row => row.map(cell).join(';')).join('\r\n') + '\r\n'
}

export function voiceBackupJson(backup) {
    return JSON.stringify(backup, null, 2)
}
