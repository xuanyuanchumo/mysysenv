import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Dialog {
    id: deleteVersionDialog
    title: qsTr("确认删除版本")
    modal: true
    standardButtons: Dialog.Ok | Dialog.Cancel
    visible: false

    property string version: ""
    signal deleteAccepted(string version)

    ColumnLayout {
        spacing: 10

        Text {
            text: qsTr("确定要删除版本 ") + deleteVersionDialog.version + qsTr(" 吗？\n此操作无法撤销。")
            font.pixelSize: 14
            color: "#333333"
        }
    }

    onAccepted: {
        if (backend) backend.logInfo("[QML] DeleteVersionDialog accepted for version: " + version)
        if (version !== "") {
            try {
                deleteAccepted(version)
            } catch (e) {
                if (backend) backend.logError("[QML] Error in deleteAccepted callback: " + e)
            } finally {
                version = ""
            }
        } else {
            if (backend) backend.logWarning("[QML] DeleteVersionDialog accepted but no version specified")
        }
    }

    onRejected: {
        if (backend) backend.logDebug("[QML] DeleteVersionDialog rejected")
        version = ""
    }

    function openDialog(ver: string) {
        if (backend) backend.logDebug("[QML] Opening DeleteVersionDialog for version: " + ver)
        if (ver !== "") {
            version = ver
            open()
        } else {
            if (backend) backend.logError("[QML] Cannot open DeleteVersionDialog: no version specified")
        }
    }
}
