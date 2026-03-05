; mouse_control.ahk - Scripts de automação de interface
; Controle de mouse/teclado para abrir PDF, centralizar janelas, etc.

#Requires AutoHotkey v2.0

; Hotkeys de exemplo (descomente e ajuste conforme necessidade)
; ^!l::Run "C:\caminho\para\arquivo.pdf"  ; Ctrl+Alt+L abre PDF
; ^!c::WinCenter("A")                     ; Ctrl+Alt+C centraliza janela

; Funcao para centralizar janela ativa
WinCenter(win) {
    try {
        WinGetPos &x, &y, &w, &h, win
        mon := WinGetMonitor(win)
        SysGet &monLeft, 76, mon
        SysGet &monTop, 77, mon
        SysGet &monRight, 78, mon
        SysGet &monBottom, 79, mon
        newX := (monRight - monLeft - w) // 2 + monLeft
        newY := (monBottom - monTop - h) // 2 + monTop
        WinMove newX, newY,,, win
    }
}
