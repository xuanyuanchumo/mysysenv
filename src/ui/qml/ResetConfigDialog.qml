import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Dialog {
    id: resetConfigDialog
    title: qsTr("确认恢复默认配置")
    modal: true
    standardButtons: Dialog.Ok | Dialog.Cancel

    signal resetAccepted()

    ColumnLayout {
        spacing: 10

        Text {
            text: qsTr("确定要恢复默认配置吗？\n此操作将删除所有自定义配置，无法撤销。")
            font.pixelSize: 14
            color: "#333333"
        }
    }

    onAccepted: {
        resetAccepted()
    }
}
