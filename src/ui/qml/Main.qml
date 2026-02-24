import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: root
    visible: true
    
    Theme {
        id: theme
    }
    
    width: 1024
    height: 768
    minimumWidth: 800
    minimumHeight: 600
    title: qsTr("Mysysenv - 系统环境管理器")
    flags: Qt.FramelessWindowHint | Qt.Window
    x: (Screen.width - width) / 2
    y: (Screen.height - height) / 2
    color: theme.backgroundColor
    property bool isMaximized: root.visibility === Window.Maximized
    
    property var expandedGroups: []
    property bool editingMode: false
    property string configContext: ""
    
    function toggleGroup(majorVersion) {
        if (backend) backend.logDebug("[QML] toggleGroup called with majorVersion: " + majorVersion)
        var idx = expandedGroups.indexOf(majorVersion)
        if (idx >= 0) {
            expandedGroups.splice(idx, 1)
        } else {
            expandedGroups.push(majorVersion)
        }
        expandedGroupsChanged()
    }
    
    function isGroupExpanded(majorVersion) {
        return expandedGroups.indexOf(majorVersion) >= 0
    }
    
    DeleteVersionDialog {
        id: deleteVersionDialog
        onDeleteAccepted: (version) => {
            if (backend) backend.logInfo("[QML] DeleteVersionDialog accepted for version: " + version)
            if (backend && version) {
                try {
                    backend.deleteVersion(version)
                } catch (e) {
                    backend.logError("[QML] Error calling backend.deleteVersion: " + e)
                }
            } else if (!backend) {
                backend.logError("[QML] Backend not available, cannot delete version")
            }
        }
    }
    
    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            color: theme.surfaceColor
            
            MouseArea {
                anchors.fill: parent
                
                onPressed: {
                    root.startSystemMove()
                }
                
                onDoubleClicked: {
                    root.visibility = root.visibility === Window.FullScreen ? Window.Windowed : (root.visibility === Window.Maximized ? Window.Windowed : Window.Maximized)
                }
            }
            
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 20
                anchors.rightMargin: 12
                spacing: 12
                
                Text {
                    text: qsTr("Mysysenv")
                    font.pixelSize: 16
                    font.bold: true
                    color: theme.textPrimary
                }
                
                Rectangle {
                    width: adminLabel.width + 16
                    height: 22
                    radius: 11
                    color: backend && backend.isAdmin ? "#d1fae5" : "#fef3c7"
                    
                    Text {
                        id: adminLabel
                        text: backend && backend.isAdmin ? qsTr("管理员模式") : qsTr("非管理员模式")
                        font.pixelSize: 11
                        font.bold: true
                        color: backend && backend.isAdmin ? "#059669" : "#d97706"
                        anchors.centerIn: parent
                    }
                }
                
                Item { Layout.fillWidth: true }
                
                Rectangle {
                    id: minimizeBtn
                    width: 32
                    height: 32
                    color: mouseAreaMinimize.containsMouse ? "#f3f4f6" : "transparent"
                    radius: 8
                    
                    Behavior on color {
                        ColorAnimation { duration: 150 }
                    }
                    
                    MouseArea {
                        id: mouseAreaMinimize
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: root.showMinimized()
                        
                        Rectangle {
                            anchors.centerIn: parent
                            width: 12
                            height: 2
                            color: theme.textSecondary
                            radius: 1
                        }
                    }
                }
                
                Rectangle {
                    id: maximizeBtn
                    width: 32
                    height: 32
                    color: mouseAreaMaximize.containsMouse ? "#f3f4f6" : "transparent"
                    radius: 8
                    
                    Behavior on color {
                        ColorAnimation { duration: 150 }
                    }
                    
                    MouseArea {
                        id: mouseAreaMaximize
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: root.visibility = root.visibility === Window.Maximized ? Window.Windowed : Window.Maximized
                        
                        Rectangle {
                            anchors.centerIn: parent
                            width: root.isMaximized ? 8 : 10
                            height: root.isMaximized ? 8 : 10
                            color: "transparent"
                            border.color: theme.textSecondary
                            border.width: 2
                            radius: 1
                            
                            Rectangle {
                                visible: root.isMaximized
                                anchors.top: parent.top
                                anchors.left: parent.left
                                width: 10
                                height: 10
                                color: "transparent"
                                border.color: theme.textSecondary
                                border.width: 2
                                radius: 1
                                anchors.topMargin: -4
                                anchors.leftMargin: 4
                            }
                        }
                    }
                }
                
                Rectangle {
                    id: closeBtn
                    width: 32
                    height: 32
                    color: mouseAreaClose.containsMouse ? "#fee2e2" : "transparent"
                    radius: 8
                    
                    Behavior on color {
                        ColorAnimation { duration: 150 }
                    }
                    
                    MouseArea {
                        id: mouseAreaClose
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: root.close()
                        
                        Item {
                            anchors.centerIn: parent
                            width: 12
                            height: 12
                            
                            Rectangle {
                                anchors.centerIn: parent
                                width: 12
                                height: 2
                                color: mouseAreaClose.containsMouse ? "#dc2626" : theme.textSecondary
                                rotation: 45
                                radius: 1
                            }
                            
                            Rectangle {
                                anchors.centerIn: parent
                                width: 12
                                height: 2
                                color: mouseAreaClose.containsMouse ? "#dc2626" : theme.textSecondary
                                rotation: -45
                                radius: 1
                            }
                        }
                    }
                }
            }
        }
        
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0
            
            Sidebar {
                id: sidebar
                theme: root.theme
                stackView: stackView
                configPanel: configPanel
                configContext: root.configContext
                editingMode: root.editingMode
                onConfigButtonClicked: {
                    root.configContext = sidebar.configContext
                }
                onToolSelected: {
                    if (backend) backend.logInfo("[QML] Tool selected: " + (backend.currentTool || "none"))
                }
            }
            
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: theme.backgroundColor
                
                StackView {
                    id: stackView
                    anchors.fill: parent
                    initialItem: versionPanel
                }
            }
        }
        
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 44
            color: theme.surfaceColor
            border.color: theme.borderColor
            border.width: 1
            
            ColumnLayout {
                anchors.fill: parent
                anchors.leftMargin: 24
                anchors.rightMargin: 24
                anchors.topMargin: 4
                anchors.bottomMargin: 4
                spacing: 4
                
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    
                    ProgressBar {
                        id: progressBar
                        Layout.fillWidth: true
                        Layout.preferredHeight: 8
                        from: 0
                        to: 100
                        value: (backend && backend.downloadInProgress) ? backend.downloadProgress : 0
                        visible: backend && backend.downloadInProgress
                    }
                    
                    Text {
                        id: progressPercent
                        visible: backend && backend.downloadInProgress
                        text: (backend && backend.downloadInProgress) ? (backend.downloadProgress + "%") : "0%"
                        font.pixelSize: 12
                        font.bold: true
                        color: theme.primaryColor
                    }
                }
                
                Text {
                    id: statusText
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    verticalAlignment: Text.AlignVCenter
                    text: {
                        if (backend && backend.downloadInProgress) {
                            var toolName = backend.downloadToolName || ""
                            var version = backend.downloadingVersion || ""
                            var downloaded = backend.format_file_size(backend.downloadedBytes)
                            var total = backend.format_file_size(backend.totalBytes)
                            if (toolName && version) {
                                return "正在下载 " + toolName + " " + version + " - " + downloaded + "/" + total
                            } else if (toolName) {
                                return "正在下载 " + toolName + " - " + downloaded + "/" + total
                            } else {
                                return "正在下载 - " + downloaded + "/" + total
                            }
                        } else {
                            return backend ? backend.message : ""
                        }
                    }
                    font.pixelSize: 12
                    color: theme.textSecondary
                    elide: Text.ElideRight
                }
            }
        }
    }
    
    Component {
        id: versionPanel
        
        VersionPanel {
            theme: root.theme
            expandedGroups: root.expandedGroups
            deleteDialog: deleteVersionDialog
        }
    }
    
    Component {
        id: configPanel
        
        ConfigPanel {
            theme: root.theme
            configContext: root.configContext
            editingMode: root.editingMode
            stackView: stackView
            onGoBack: {
                if (stackView && stackView.depth > 1) {
                    stackView.pop()
                }
            }
        }
    }
    
    Connections {
        target: backend
        enabled: !!backend
        
        function onCurrentToolChanged() {
            if (backend) backend.logDebug("[QML] Current tool changed to: " + backend.currentTool)
            if (backend && backend.currentTool !== "") {
                backend.loadConfig()
            }
        }
    }
    
    Component.onCompleted: {
        if (backend) {
            backend.logInfo("[QML] Main.qml component initialized")
            backend.logDebug("[QML] Loading config...")
            backend.loadConfig()
        }
    }
}
