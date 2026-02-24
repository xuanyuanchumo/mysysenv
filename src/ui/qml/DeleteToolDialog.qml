import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Dialog {
    id: deleteToolDialog
    title: qsTr("确认删除工具配置")
    modal: true
    standardButtons: Dialog.Ok | Dialog.Cancel

    property string toolName: ""
    signal deleteAccepted(string toolName)

    ColumnLayout {
        spacing: 10

        Text {
            text: qsTr("确定要删除 ") + deleteToolDialog.toolName.toUpperCase() + qsTr(" 的配置吗？\n此操作无法撤销。")
            font.pixelSize: 14
            color: "#333333"
        }
    }

    onAccepted: {
        if (backend) backend.logInfo("[QML] DeleteToolDialog accepted for tool: " + toolName)
        if (toolName !== "") {
            try {
                deleteAccepted(toolName)
            } catch (e) {
                if (backend) backend.logError("[QML] Error in deleteAccepted callback: " + e)
            } finally {
                toolName = ""
            }
        } else {
            if (backend) backend.logWarning("[QML] DeleteToolDialog accepted but no tool specified")
        }
    }

    onRejected: {
        if (backend) backend.logDebug("[QML] DeleteToolDialog rejected")
        toolName = ""
    }

    function openDialog(tool: string) {
        if (backend) backend.logDebug("[QML] Opening DeleteToolDialog for tool: " + tool)
        if (tool !== "") {
            toolName = tool
            open()
        } else {
            if (backend) backend.logError("[QML] Cannot open DeleteToolDialog: no tool specified")
        }
    }
}
