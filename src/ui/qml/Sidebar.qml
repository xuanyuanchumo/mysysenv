
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    property var theme
    property var stackView
    property var configPanel
    property string configContext: ""
    property bool editingMode: false

    signal configButtonClicked()
    signal toolSelected()

    Layout.preferredWidth: 240
    Layout.fillHeight: true
    color: "#ffffff"
    border.color: theme ? theme.borderColor : "#e5e7eb"
    border.width: 0

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        anchors.topMargin: 0
        anchors.rightMargin: 16
        anchors.bottomMargin: 16
        anchors.leftMargin: 16
        spacing: 12

        Text {
            text: qsTr("工具列表")
            font.pixelSize: 15
            font.bold: true
            color: theme ? theme.textPrimary : "#000000"
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#f9fafb"
            radius: 10
            border.color: "#e5e7eb"
            border.width: 1

            ListView {
                id: toolList
                anchors.fill: parent
                anchors.margins: 8
                model: backend ? backend.tools : []
                clip: true
                spacing: 6

                delegate: Item {
                    id: delegateItem
                    width: toolList.width
                    height: 48

                    property bool isSelected: backend ? (backend.currentTool === modelData.name) : false
                    property bool hovered: false

                    Rectangle {
                        anchors.fill: parent
                        color: isSelected ? (theme ? theme.primaryColor : "#3b82f6") : (hovered ? "#f3f4f6" : "transparent")
                        radius: 8

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 16
                            anchors.rightMargin: 16

                            Text {
                                text: modelData.name.toUpperCase()
                                font.pixelSize: 14
                                font.bold: isSelected
                                color: isSelected ? "#ffffff" : "#111827"
                                verticalAlignment: Text.AlignVCenter
                            }

                            Item { 
                                Layout.fillWidth: true 
                            }

                            Rectangle {
                                width: 8
                                height: 8
                                radius: 4
                                color: isSelected ? "#ffffff" : "transparent"
                            }
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        hoverEnabled: true
                        onEntered: delegateItem.hovered = true
                        onExited: delegateItem.hovered = false
                        cursorShape: Qt.PointingHandCursor

                        onClicked: {
                        if (backend) backend.logDebug("[QML] Tool list item clicked: " + modelData.name)
                        if (backend) {
                            if (backend.currentTool === modelData.name) {
                                backend.currentTool = ""
                            } else {
                                backend.currentTool = modelData.name
                            }
                        }
                        if (stackView) {
                            while (stackView.depth > 1) {
                                stackView.pop()
                            }
                        }
                        root.toolSelected()
                    }
                    }
                }

                ScrollBar.vertical: ScrollBar {
                    active: true
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 48
            color: parent.hovered ? (theme ? theme.primaryDark : "#2563eb") : (theme ? theme.primaryColor : "#3b82f6")
            radius: 10
            property bool hovered: false

            Text {
                anchors.centerIn: parent
                text: qsTr("配置管理")
                font.pixelSize: 14
                font.bold: true
                color: "#ffffff"
            }

            MouseArea {
                id: configBtnMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor

                onEntered: parent.hovered = true
                onExited: parent.hovered = false

                onClicked: {
                    if (backend) backend.logInfo("[QML] Config button clicked")
                    if (backend) {
                        if (backend.currentTool !== "") {
                            root.configContext = backend.currentTool
                            backend.logDebug("[QML] Loading tool-specific config for: " + backend.currentTool)
                            backend.loadToolSpecificConfig(backend.currentTool)
                        } else {
                            root.configContext = ""
                            backend.logDebug("[QML] Loading general config")
                            backend.loadConfig()
                        }
                    }
                    if (stackView && configPanel) {
                        var currentItem = stackView.currentItem
                        if (currentItem && currentItem.parent && currentItem.parent.id === "configPanel") {
                            return
                        }
                        while (stackView.depth > 1) {
                            stackView.pop()
                        }
                        stackView.push(configPanel)
                    }
                    root.configButtonClicked()
                }
            }
        }
    }
}

