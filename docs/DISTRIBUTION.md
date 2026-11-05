# Distribution model

The project distributes its own source, launchers, transforms, package digests and tests. It does **not** host or attach an original or modified SteamOS image, Valve client binary, upstream EDID or third-party plugin binary.

Users obtain SteamOS from [Valve's official download and agreement page](https://store.steampowered.com/steamos/download/?ver=steamdeck), accept the terms themselves, and patch their own local image, then flash it with a separate writer such as Rufus. Valve's agreement describes a mixture of open-source and proprietary components and restricts reproduction/redistribution outside its terms. This is the reason to avoid treating the entire image as freely redistributable. The patcher-only model reduces what this project redistributes; it is not a legal opinion that every use or upstream modification is permitted.

Upstream material retains its own terms. The optional InnoVision integration downloads a fixed revision locally rather than redistributing its full script. The optional EDID/plugins are downloaded from upstream and checksum-verified. See SOURCES.md for provenance. No Valve branding or official support relationship is claimed.
