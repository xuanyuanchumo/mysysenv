import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Dialog {
    id: addToolDialog
    title: qsTr("添加工具配置")
    modal: true
    standardButtons: Dialog.Ok | Dialog.Cancel

    signal toolNameAccepted(string name)

    ColumnLayout {
        spacing: 10

        Text {
            text: qsTr("请输入工具名称:")
            font.pixelSize: 14
        }

        TextField {
            id: toolNameInput
            placeholderText: qsTr("例如: go, rust, dotnet")
            Layout.preferredWidth: 250
            focus: true
        }
    }

    onAccepted: {
        if (toolNameInput.text.trim() !== "") {
            toolNameAccepted(toolNameInput.text)
            toolNameInput.text = ""
        }
    }

    onRejected: {
        toolNameInput.text = ""
    }
}
