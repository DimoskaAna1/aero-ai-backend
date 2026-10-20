// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "AgentBubble",
    platforms: [.iOS(.v15)],
    products: [
        .library(name: "AgentBubble", targets: ["AgentBubble"]),
    ],
    targets: [
        .target(name: "AgentBubble"),
    ]
)
