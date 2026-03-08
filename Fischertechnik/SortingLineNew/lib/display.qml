// auto generated content from display configuration
import QtQuick 2.2
import QtQuick.Window 2.0
import QtQuick.Controls 1.1
import QtQuick.Controls.Styles 1.1
import QtQuick.Extras 1.4

TXTWindow {
  Rectangle {
    id: rect
    color: "grey"
    anchors.fill: parent
  }
  TXTLabel {
    id: img_label
    text: ""
    font.pixelSize: 16
    font.bold: false
    font.italic: false
    font.underline: false
    horizontalAlignment: Text.AlignLeft
    color: "#ffffff"
    elide: Text.ElideRight
    x: 20
    y: 20
    width: 200
    height: 150
  }
  StatusIndicator {
    id: red
    color: "#EC1600"
    active: false
    x: 70
    y: 195
    width: 35
    height: 35
  }
  StatusIndicator {
    id: white
    color: "#FFFFFF"
    active: false
    x: 0
    y: 195
    width: 35
    height: 35
  }
  StatusIndicator {
    id: blue
    color: "#005693"
    active: false
    x: 135
    y: 195
    width: 35
    height: 35
  }
  StatusIndicator {
    id: fail
    color: "#E7AE13"
    active: false
    x: 205
    y: 195
    width: 35
    height: 35
  }
  TXTLabel {
    id: version_label
    text: "Sorting Line AI: Version 2023/01/20"
    font.pixelSize: 16
    font.bold: false
    font.italic: false
    font.underline: false
    horizontalAlignment: Text.AlignLeft
    color: "#ffffff"
    elide: Text.ElideRight
    x: 20
    y: 0
    width: 200
    height: 20
  }
  TXTLabel {
    id: part_pass_fail
    text: "<font>Webadress loading...</font>"
    font.pixelSize: 16
    font.bold: false
    font.italic: false
    font.underline: false
    horizontalAlignment: Text.AlignLeft
    color: "#ffffff"
    elide: Text.ElideRight
    x: 20
    y: 170
    width: 200
    height: 20
  }
}
