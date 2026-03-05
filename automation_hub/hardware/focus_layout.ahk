; focus_layout.ahk - Arruma janelas para modo leitura
; Centraliza/redimensiona janelas no monitor

; Exemplo: maximiza janela ativa e centraliza
; Ajuste conforme seu layout preferido

#Requires AutoHotkey v2.0

; Maximiza a janela ativa para modo leitura
WinMaximize "A"

; Opcional: fecha notificacoes do Windows
; DllCall("Shell32.dll\Shell_NotifyIcon", "Int", 2, "Ptr", 0)
