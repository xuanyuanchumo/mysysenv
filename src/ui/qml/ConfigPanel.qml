import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

ColumnLayout {
    id: configPanelRoot
    spacing: 16

    property var theme: null
    property string configContext: ""
    property bool editingMode: false
    property var stackView: null

    signal goBack()

    Dialog {
        id: addToolDialog
        title: qsTr("添加工具配置")
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel

        signal toolNameAccepted(string name)

        onToolNameAccepted: (name) => {
            if (backend) backend.logInfo("[QML] AddToolDialog accepted toolName: " + name)
            if (backend && backend.addToolConfig(name)) {
                backend.logInfo("[QML] Tool config added, loading config...")
                backend.loadConfig()
                while (configPanelRoot.stackView.depth > 1) {
                    configPanelRoot.stackView.pop()
                }
                configPanelRoot.editingMode = true
            }
        }

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
                addToolDialog.toolNameAccepted(toolNameInput.text)
                toolNameInput.text = ""
            }
        }

        onRejected: {
            toolNameInput.text = ""
        }
    }

    Dialog {
        id: resetConfigDialog
        title: qsTr("恢复默认配置")
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel

        signal resetAccepted()

        onResetAccepted: () => {
            if (backend) backend.logInfo("[QML] ResetConfigDialog accepted, resetting to default config...")
            if (backend) backend.resetToDefaultConfig()
        }

        ColumnLayout {
            spacing: 10

            Text {
                text: qsTr("确定要恢复默认配置吗？\n此操作将覆盖当前所有配置，无法撤销。")
                font.pixelSize: 14
                color: "#333333"
            }
        }

        onAccepted: {
            resetConfigDialog.resetAccepted()
        }
    }

    Dialog {
        id: deleteToolDialog
        title: qsTr("确认删除工具配置")
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel

        property string toolName: ""
        signal deleteAccepted(string toolName)

        onDeleteAccepted: (toolName) => {
            if (backend) backend.logInfo("[QML] DeleteToolDialog accepted for toolName: " + toolName)
            if (backend && backend.deleteToolConfig(toolName)) {
                configPanelRoot.configContext = ""
                backend.loadConfig()
                while (configPanelRoot.stackView.depth > 1) {
                    configPanelRoot.stackView.pop()
                }
            }
        }

        ColumnLayout {
            spacing: 10

            Text {
                text: qsTr("确定要删除 ") + deleteToolDialog.toolName.toUpperCase() + qsTr(" 的配置吗？\n此操作无法撤销。")
                font.pixelSize: 14
                color: "#333333"
            }
        }

        onAccepted: {
            if (toolName !== "") {
                deleteToolDialog.deleteAccepted(toolName)
                toolName = ""
            }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.margins: 24

        Text {
            text: configPanelRoot.configContext !== "" ? 
                  qsTr("配置管理 - ") + configPanelRoot.configContext.toUpperCase() : 
                  qsTr("配置管理")
            font.pixelSize: 28
            font.bold: true
            color: theme ? theme.textPrimary : "#000000"
        }

        Item { Layout.fillWidth: true }

        Rectangle {
            width: 80
            height: 36
            color: parent.hovered ? "#374151" : "#6b7280"
            radius: 8
            property bool hovered: false

            Behavior on color {
                ColorAnimation { duration: 150 }
            }

            Text {
                anchors.centerIn: parent
                text: qsTr("返回")
                font.pixelSize: 13
                font.bold: true
                color: "#ffffff"
            }

            MouseArea {
                id: backBtn
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor

                onEntered: parent.hovered = true
                onExited: parent.hovered = false

                onClicked: {
                    if (backend) backend.logDebug("[QML] Config panel go back clicked")
                    configPanelRoot.goBack()
                }
            }
        }
    }

    Rectangle {
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.margins: 24
        color: theme ? theme.surfaceColor : "#ffffff"
        radius: 12
        border.color: theme ? theme.borderColor : "#e5e7eb"
        border.width: 1

        ScrollView {
            anchors.fill: parent
            anchors.margins: 16

            TextArea {
                id: configTextArea
                text: backend ? backend.configJson : ""
                font.family: "Consolas"
                font.pixelSize: 13
                selectByMouse: true
                wrapMode: TextArea.Wrap
                readOnly: !configPanelRoot.editingMode
                color: theme ? theme.textPrimary : "#000000"
                selectionColor: theme ? theme.primaryColor : "#3b82f6"
                selectedTextColor: "#ffffff"
            }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.margins: 24
        spacing: 10

        Rectangle {
            width: 96
            height: 38
            color: parent.hovered ? (theme ? theme.primaryDark : "#2563eb") : (theme ? theme.primaryColor : "#3b82f6")
            radius: 8
            property bool hovered: false

            Behavior on color {
                ColorAnimation { duration: 150 }
            }

            Text {
                anchors.centerIn: parent
                text: qsTr("加载配置")
                font.pixelSize: 13
                font.bold: true
                color: "#ffffff"
            }

            MouseArea {
                id: loadBtn
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor

                onEntered: parent.hovered = true
                onExited: parent.hovered = false

                onClicked: {
                    if (backend) {
                        if (configPanelRoot.configContext !== "") {
                            backend.logInfo("[QML] Loading tool-specific config for: " + configPanelRoot.configContext)
                            backend.loadToolSpecificConfig(configPanelRoot.configContext)
                        } else {
                            backend.logInfo("[QML] Loading general config")
                            backend.loadConfig()
                        }
                    }
                }
            }
        }

        Rectangle {
            width: 96
            height: 38
            color: parent.hovered ? "#374151" : "#6b7280"
            radius: 8
            property bool hovered: false

            Behavior on color {
                ColorAnimation { duration: 150 }
            }

            Text {
                anchors.centerIn: parent
                text: configPanelRoot.editingMode ? qsTr("取消编辑") : qsTr("编辑配置")
                font.pixelSize: 13
                font.bold: true
                color: "#ffffff"
            }

            MouseArea {
                id: editBtn
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor

                onEntered: parent.hovered = true
                onExited: parent.hovered = false

                onClicked: {
                    if (backend) backend.logDebug("[QML] Toggling edit mode to: " + (!configPanelRoot.editingMode))
                    configPanelRoot.editingMode = !configPanelRoot.editingMode
                }
            }
        }

        Rectangle {
            visible: configPanelRoot.editingMode
            width: 96
            height: 38
            color: parent.hovered ? "#059669" : (theme ? theme.successColor : "#10b981")
            radius: 8
            property bool hovered: false

            Behavior on color {
                ColorAnimation { duration: 150 }
            }

            Text {
                anchors.centerIn: parent
                text: qsTr("保存配置")
                font.pixelSize: 13
                font.bold: true
                color: "#ffffff"
            }

            MouseArea {
                id: saveBtn
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor

                onEntered: parent.hovered = true
                onExited: parent.hovered = false

                onClicked: {
                    if (backend) {
                        if (configPanelRoot.configContext !== "") {
                            backend.logInfo("[QML] Saving tool-specific config for: " + configPanelRoot.configContext)
                            backend.saveToolSpecificConfig(configPanelRoot.configContext, configTextArea.text)
                        } else {
                            backend.logInfo("[QML] Saving general config")
                            backend.saveConfig(configTextArea.text)
                        }
                    }
                }
            }
        }

        Rectangle {
            visible: configPanelRoot.configContext === ""
            width: 112
            height: 38
            color: parent.hovered ? "#b91c1c" : (theme ? theme.dangerColor : "#ef4444")
            radius: 8
            property bool hovered: false

            Behavior on color {
                ColorAnimation { duration: 150 }
            }

            Text {
                anchors.centerIn: parent
                text: qsTr("恢复默认配置")
                font.pixelSize: 13
                font.bold: true
                color: "#ffffff"
            }

            MouseArea {
                id: resetBtn
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor

                onEntered: parent.hovered = true
                onExited: parent.hovered = false

                onClicked: {
                    if (backend) backend.logInfo("[QML] Opening reset config dialog")
                    resetConfigDialog.open()
                }
            }
        }

        Rectangle {
            visible: configPanelRoot.configContext === ""
            width: 96
            height: 38
            color: parent.hovered ? "#374151" : "#6b7280"
            radius: 8
            property bool hovered: false

            Behavior on color {
                ColorAnimation { duration: 150 }
            }

            Text {
                anchors.centerIn: parent
                text: qsTr("清空缓存")
                font.pixelSize: 13
                font.bold: true
                color: "#ffffff"
            }

            MouseArea {
                id: clearCacheBtn
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor

                onEntered: parent.hovered = true
                onExited: parent.hovered = false

                onClicked: {
                    if (backend) {
                        backend.logInfo("[QML] Clearing cache")
                        backend.clearCache()
                    }
                }
            }
        }

        Rectangle {
            width: 112
            height: 38
            color: parent.hovered ? "#374151" : "#6b7280"
            radius: 8
            property bool hovered: false

            Behavior on color {
                ColorAnimation { duration: 150 }
            }

            Text {
                anchors.centerIn: parent
                text: qsTr("添加工具配置")
                font.pixelSize: 13
                font.bold: true
                color: "#ffffff"
            }

            MouseArea {
                id: addBtn
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor

                onEntered: parent.hovered = true
                onExited: parent.hovered = false

                onClicked: {
                    if (backend) backend.logInfo("[QML] Opening add tool dialog")
                    addToolDialog.open()
                }
            }
        }

        Rectangle {
            visible: configPanelRoot.configContext !== ""
            width: 112
            height: 38
            color: parent.hovered ? "#b91c1c" : (theme ? theme.dangerColor : "#ef4444")
            radius: 8
            property bool hovered: false

            Behavior on color {
                ColorAnimation { duration: 150 }
            }

            Text {
                anchors.centerIn: parent
                text: qsTr("删除工具配置")
                font.pixelSize: 13
                font.bold: true
                color: "#ffffff"
            }

            MouseArea {
                id: delBtn
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor

                onEntered: parent.hovered = true
                onExited: parent.hovered = false

                onClicked: {
                    if (backend) backend.logInfo("[QML] Opening delete tool dialog for: " + configPanelRoot.configContext)
                    deleteToolDialog.toolName = configPanelRoot.configContext
                    deleteToolDialog.open()
                }
            }
        }

        Item { Layout.fillWidth: true }
    }
}
