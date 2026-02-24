import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: versionPanelRoot
    spacing: 16

    property var theme: null
    property var expandedGroups: []
    property var deleteDialog: null

    function toggleGroup(majorVersion) {
        if (backend) backend.logDebug("[QML] toggleGroup called for majorVersion: " + majorVersion)
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

    RowLayout {
        Layout.fillWidth: true
        Layout.margins: 24

        Text {
            text: backend ? (backend.currentTool ? backend.currentTool.toUpperCase() : qsTr("请选择工具")) : ""
            font.pixelSize: 28
            font.bold: true
            color: theme ? theme.textPrimary : "#000000"
        }

        Item { Layout.fillWidth: true }

        Rectangle {
            visible: !!backend && !!backend.currentTool && backend.currentTool !== ""
            width: currentVersionLabel.width + 24
            height: 32
            radius: 8
            color: "#eff6ff"
            border.color: "#bfdbfe"
            border.width: 1

            Text {
                id: currentVersionLabel
                text: qsTr("当前版本: ") + (backend ? (backend.currentVersion || qsTr("未设置")) : qsTr("未设置"))
                font.pixelSize: 13
                font.bold: true
                color: "#1d4ed8"
                anchors.centerIn: parent
            }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.margins: 24
        spacing: 20

        ColumnLayout {
            Layout.preferredWidth: 6
            Layout.fillWidth: true
            Layout.fillHeight: true

            RowLayout {
                Layout.fillWidth: true

                Text {
                    text: qsTr("已安装版本")
                    font.pixelSize: 18
                    font.bold: true
                    color: theme ? theme.textPrimary : "#000000"
                }

                Item { Layout.fillWidth: true }

                Rectangle {
                    width: 80
                    height: 36
                    color: parent.hovered ? (theme ? theme.primaryDark : "#2563eb") : (theme ? theme.primaryColor : "#3b82f6")
                    radius: 8
                    property bool hovered: false

                    Behavior on color {
                        ColorAnimation { duration: 150 }
                    }

                    Text {
                        anchors.centerIn: parent
                        text: qsTr("刷新")
                        font.pixelSize: 13
                        font.bold: true
                        color: "#ffffff"
                    }

                    MouseArea {
                        id: installedRefreshBtn
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor

                        onEntered: parent.hovered = true
                        onExited: parent.hovered = false

                        onClicked: {
                            if (backend) backend.logInfo("[QML] Refreshing installed versions")
                            if (backend) {
                                try {
                                    backend.loadInstalledVersions()
                                } catch (e) {
                                    backend.logError("[QML] Error calling backend.loadInstalledVersions: " + e)
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: theme ? theme.surfaceColor : "#ffffff"
                radius: 12
                border.color: theme ? theme.borderColor : "#e5e7eb"
                border.width: 1

                ListView {
                    id: installedList
                    anchors.fill: parent
                    anchors.margins: 10
                    model: backend ? backend.installedVersions : []
                    clip: true
                    spacing: 8

                    delegate: Rectangle {
                        width: installedList.width
                        height: 56
                        color: (modelData && backend && modelData.version === backend.currentVersion) ? "#eff6ff" : (hovered ? (theme ? theme.surfaceHover : "#f3f4f6") : "transparent")
                        radius: 8
                        border.color: (modelData && backend && modelData.version === backend.currentVersion) ? "#bfdbfe" : (hovered ? (theme ? theme.borderColor : "#e5e7eb") : "transparent")
                        border.width: 1

                        property bool hovered: false
                        property bool dataIsSystem: modelData ? (modelData.isSystem || false) : false
                        property bool dataLocked: modelData ? (modelData.locked || false) : false

                        Behavior on color {
                            ColorAnimation { duration: 150 }
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 16
                            anchors.rightMargin: 16

                            Text {
                                text: modelData ? modelData.version : ""
                                font.pixelSize: 15
                                font.bold: true
                                color: theme ? theme.textPrimary : "#000000"
                            }

                            Rectangle {
                                visible: dataIsSystem
                                width: systemText.width + 12
                                height: 20
                                radius: 10
                                color: "#fef3c7"

                                Text {
                                    id: systemText
                                    text: qsTr("系统")
                                    font.pixelSize: 10
                                    font.bold: true
                                    color: "#d97706"
                                    anchors.centerIn: parent
                                }
                            }

                            Rectangle {
                                visible: dataLocked
                                width: lockedText.width + 12
                                height: 20
                                radius: 10
                                color: "#fee2e2"

                                Text {
                                    id: lockedText
                                    text: qsTr("已锁定")
                                    font.pixelSize: 10
                                    font.bold: true
                                    color: "#dc2626"
                                    anchors.centerIn: parent
                                }
                            }

                            Rectangle {
                                visible: modelData && backend && modelData.version === backend.currentVersion
                                width: currentText.width + 12
                                height: 20
                                radius: 10
                                color: "#d1fae5"

                                Text {
                                    id: currentText
                                    text: qsTr("当前")
                                    font.pixelSize: 10
                                    font.bold: true
                                    color: "#059669"
                                    anchors.centerIn: parent
                                }
                            }

                            Item { Layout.fillWidth: true }

                            Rectangle {
                                visible: modelData && backend && modelData.version !== backend.currentVersion
                                width: 64
                                height: 32
                                color: parent.hovered ? (theme ? theme.primaryDark : "#2563eb") : (dataIsSystem ? "#e5e7eb" : (theme ? theme.primaryColor : "#3b82f6"))
                                radius: 8
                                enabled: !dataIsSystem
                                property bool hovered: false
                                z: 1

                                Behavior on color {
                                    ColorAnimation { duration: 150 }
                                }

                                Text {
                                    anchors.centerIn: parent
                                    text: qsTr("切换")
                                    font.pixelSize: 12
                                    font.bold: true
                                    color: dataIsSystem ? "#9ca3af" : "#ffffff"
                                }

                                MouseArea {
                                    id: switchBtn
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    enabled: modelData && !modelData.isSystem
                                    cursorShape: Qt.PointingHandCursor
                                    z: 2

                                    onEntered: {
                                        if (parent.enabled) parent.hovered = true
                                        parent.parent.parent.hovered = true
                                    }
                                    onExited: {
                                        parent.hovered = false
                                        parent.parent.parent.hovered = false
                                    }

                                    onClicked: {
                                        if (backend) backend.logInfo("[QML] Switching to version: " + modelData.version)
                                        if (backend && modelData && modelData.version) {
                                            try {
                                                backend.switchVersion(modelData.version)
                                            } catch (e) {
                                                backend.logError("[QML] Error calling backend.switchVersion: " + e)
                                            }
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                width: 64
                                height: 32
                                color: parent.hovered ? "#374151" : (dataIsSystem ? "#e5e7eb" : "#6b7280")
                                radius: 8
                                enabled: !dataIsSystem
                                property bool hovered: false
                                z: 1

                                Behavior on color {
                                    ColorAnimation { duration: 150 }
                                }

                                Text {
                                    anchors.centerIn: parent
                                    text: dataLocked ? qsTr("解锁") : qsTr("锁定")
                                    font.pixelSize: 12
                                    font.bold: true
                                    color: dataIsSystem ? "#9ca3af" : "#ffffff"
                                }

                                MouseArea {
                                    id: lockBtn
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    enabled: modelData && !modelData.isSystem
                                    cursorShape: Qt.PointingHandCursor
                                    z: 2

                                    onEntered: {
                                        if (parent.enabled) parent.hovered = true
                                        parent.parent.parent.hovered = true
                                    }
                                    onExited: {
                                        parent.hovered = false
                                        parent.parent.parent.hovered = false
                                    }

                                    onClicked: {
                                        if (backend) backend.logInfo("[QML] " + (dataLocked ? "Unlocking" : "Locking") + " version: " + modelData.version)
                                        if (modelData && backend && modelData.version && backend.currentTool) {
                                            try {
                                                backend.lockVersion(backend.currentTool, modelData.version, !dataLocked)
                                            } catch (e) {
                                                backend.logError("[QML] Error calling backend.lockVersion: " + e)
                                            }
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                visible: modelData && backend && modelData.version !== backend.currentVersion
                                width: 64
                                height: 32
                                color: parent.hovered ? "#b91c1c" : ((dataLocked || dataIsSystem) ? "#e5e7eb" : (theme ? theme.dangerColor : "#ef4444"))
                                radius: 8
                                enabled: !dataLocked && !dataIsSystem
                                property bool hovered: false
                                z: 1

                                Behavior on color {
                                    ColorAnimation { duration: 150 }
                                }

                                Text {
                                    anchors.centerIn: parent
                                    text: qsTr("删除")
                                    font.pixelSize: 12
                                    font.bold: true
                                    color: (dataLocked || dataIsSystem) ? "#9ca3af" : "#ffffff"
                                }

                                MouseArea {
                                    id: deleteBtn
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    enabled: modelData && !dataLocked && !dataIsSystem
                                    cursorShape: Qt.PointingHandCursor
                                    z: 2

                                    onEntered: {
                                        if (parent.enabled) parent.hovered = true
                                        parent.parent.parent.hovered = true
                                    }
                                    onExited: {
                                        parent.hovered = false
                                        parent.parent.parent.hovered = false
                                    }

                                    onClicked: {
                                        if (backend) backend.logInfo("[QML] Opening delete dialog for version: " + modelData.version)
                                        if (deleteDialog) {
                                            deleteDialog.openDialog(modelData.version)
                                        } else {
                                            if (backend) backend.logError("[QML] Delete dialog not available")
                                        }
                                    }
                                }
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            anchors.rightMargin: 216
                            hoverEnabled: true
                            onEntered: parent.hovered = true
                            onExited: parent.hovered = false
                            z: 0
                        }
                    }

                    ScrollBar.vertical: ScrollBar {
                        active: true
                    }
                }
            }
        }

        ColumnLayout {
            Layout.preferredWidth: 4
            Layout.fillWidth: true
            Layout.fillHeight: true

            RowLayout {
                Layout.fillWidth: true

                Text {
                    text: qsTr("可下载版本")
                    font.pixelSize: 18
                    font.bold: true
                    color: theme ? theme.textPrimary : "#000000"
                }

                Text {
                    visible: !!backend && !!backend.remoteVersionsLoading
                    text: qsTr(" (加载中...)")
                    font.pixelSize: 14
                    color: theme ? theme.primaryColor : "#3b82f6"
                }

                Item { Layout.fillWidth: true }

                Rectangle {
                    width: 80
                    height: 36
                    color: parent.hovered ? (theme ? theme.primaryDark : "#2563eb") : ((!!backend && !!backend.remoteVersionsLoading) ? "#e5e7eb" : (theme ? theme.primaryColor : "#3b82f6"))
                    radius: 8
                    enabled: !!backend && !!(backend && !backend.remoteVersionsLoading)
                    property bool hovered: false

                    Behavior on color {
                        ColorAnimation { duration: 150 }
                    }

                    Text {
                        anchors.centerIn: parent
                        text: qsTr("刷新")
                        font.pixelSize: 13
                        font.bold: true
                        color: (backend && backend.remoteVersionsLoading) ? "#9ca3af" : "#ffffff"
                    }

                    MouseArea {
                        id: refreshBtn
                        anchors.fill: parent
                        hoverEnabled: true
                        enabled: !!backend && !!(backend && !backend.remoteVersionsLoading)
                        cursorShape: Qt.PointingHandCursor

                        onEntered: if (parent.enabled) parent.hovered = true
                        onExited: parent.hovered = false

                        onClicked: {
                            if (backend) backend.logInfo("[QML] Refreshing remote versions")
                            if (backend) {
                                try {
                                    backend.loadRemoteVersions()
                                } catch (e) {
                                    backend.logError("[QML] Error calling backend.loadRemoteVersions: " + e)
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: theme ? theme.surfaceColor : "#ffffff"
                radius: 12
                border.color: theme ? theme.borderColor : "#e5e7eb"
                border.width: 1

                ListView {
                    id: remoteList
                    anchors.fill: parent
                    anchors.margins: 10
                    model: backend ? backend.groupedRemoteVersions : []
                    clip: true
                    spacing: 8

                    delegate: Column {
                        width: remoteList.width

                        Rectangle {
                            id: groupHeader
                            width: parent.width
                            height: 48
                            color: groupHovered ? "#f1f5f9" : "#f8fafc"
                            radius: 8
                            border.color: theme ? theme.borderColor : "#e5e7eb"
                            border.width: 1

                            property bool groupHovered: false

                            Behavior on color {
                                ColorAnimation { duration: 150 }
                            }

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 16
                                anchors.rightMargin: 16

                                Text {
                                    text: "v" + modelData.majorVersion + ".x"
                                    font.pixelSize: 15
                                    font.bold: true
                                    color: theme ? theme.textPrimary : "#000000"
                                }

                                Rectangle {
                                    visible: modelData && modelData.hasLts
                                    width: ltsText.width + 12
                                    height: 22
                                    radius: 11
                                    color: "#d1fae5"

                                    Text {
                                        id: ltsText
                                        text: "LTS"
                                        font.pixelSize: 10
                                        font.bold: true
                                        color: "#059669"
                                        anchors.centerIn: parent
                                    }
                                }

                                Item { Layout.fillWidth: true }

                                Text {
                                    text: isGroupExpanded(modelData.majorVersion) ? "▼" : "▶"
                                    font.pixelSize: 14
                                    color: theme ? theme.textTertiary : "#9ca3af"
                                }

                                Text {
                                    text: qsTr("(") + modelData.versions.length + qsTr(" 个版本)")
                                    font.pixelSize: 13
                                    color: theme ? theme.textSecondary : "#6b7280"
                                }
                            }

                            MouseArea {
                                id: groupMouseArea
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onEntered: parent.groupHovered = true
                                onExited: parent.groupHovered = false

                                onClicked: {
                                    if (backend) backend.logDebug("[QML] Toggle version group clicked: " + modelData.majorVersion)
                                    toggleGroup(modelData.majorVersion)
                                }
                            }
                        }

                        Column {
                            width: parent.width
                            visible: isGroupExpanded(modelData.majorVersion)

                            Repeater {
                                model: modelData.versions

                                Rectangle {
                                    width: parent.width
                                    height: 56
                                    color: hovered ? (theme ? theme.surfaceHover : "#f3f4f6") : "transparent"
                                    radius: 8

                                    property bool hovered: false

                                    Behavior on color {
                                        ColorAnimation { duration: 150 }
                                    }

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 40
                                        anchors.rightMargin: 16

                                        Text {
                                            text: modelData.version
                                            font.pixelSize: 15
                                            font.bold: true
                                            color: theme ? theme.textPrimary : "#000000"
                                        }

                                        Rectangle {
                                            visible: modelData && modelData.lts
                                            width: ltsTextSmall.width + 10
                                            height: 18
                                            radius: 9
                                            color: "#d1fae5"

                                            Text {
                                                id: ltsTextSmall
                                                text: "LTS"
                                                font.pixelSize: 9
                                                font.bold: true
                                                color: "#059669"
                                                anchors.centerIn: parent
                                            }
                                        }

                                        Rectangle {
                                            visible: modelData && modelData.isInstalled
                                            width: installedText.width + 10
                                            height: 18
                                            radius: 9
                                            color: "#dbeafe"

                                            Text {
                                                id: installedText
                                                text: qsTr("已安装")
                                                font.pixelSize: 9
                                                font.bold: true
                                                color: "#2563eb"
                                                anchors.centerIn: parent
                                            }
                                        }

                                        Item { Layout.fillWidth: true }

                                        Rectangle {
                                            width: 64
                                            height: 32
                                            color: parent.hovered ? (theme ? theme.primaryDark : "#2563eb") : ((modelData && modelData.isInstalled) ? "#e5e7eb" : (theme ? theme.primaryColor : "#3b82f6"))
                                            radius: 8
                                            enabled: !(modelData && modelData.isInstalled)
                                            property bool hovered: false
                                            z: 1

                                            Behavior on color {
                                                ColorAnimation { duration: 150 }
                                            }

                                            Text {
                                                anchors.centerIn: parent
                                                text: qsTr("下载")
                                                font.pixelSize: 12
                                                font.bold: true
                                                color: (modelData && modelData.isInstalled) ? "#9ca3af" : "#ffffff"
                                            }

                                            MouseArea {
                                                id: downloadBtn
                                                anchors.fill: parent
                                                hoverEnabled: true
                                                enabled: !(modelData && modelData.isInstalled)
                                                cursorShape: Qt.PointingHandCursor
                                                z: 2

                                                onEntered: if (parent.enabled) parent.hovered = true
                                                onExited: parent.hovered = false

                                                onClicked: {
                                                    if (backend) backend.logInfo("[QML] Downloading version: " + modelData.version)
                                                    if (backend && modelData && modelData.version) {
                                                        try {
                                                            backend.downloadVersion(modelData.version)
                                                        } catch (e) {
                                                            backend.logError("[QML] Error calling backend.downloadVersion: " + e)
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        anchors.rightMargin: 80
                                        hoverEnabled: true
                                        z: 0

                                        onEntered: parent.hovered = true
                                        onExited: parent.hovered = false
                                    }
                                }
                            }
                        }
                    }

                    ScrollBar.vertical: ScrollBar {
                        active: true
                    }
                }
            }
        }
    }
}
