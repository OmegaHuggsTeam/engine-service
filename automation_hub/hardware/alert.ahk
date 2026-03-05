; alert.ahk - Alerta no monitor principal quando comando falha
; Executado pelo Kiro Cortex em caso de erro (IFTTT, webhook, etc)

#Requires AutoHotkey v2.0

; Mostra mensagem no centro do monitor principal
MsgBox "Alerta Kiro Cortex: Um comando falhou ou o IFTTT retornou erro. Verifique o log.", "Erro de Automacao", "Icon!"
