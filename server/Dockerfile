FROM debian:12-slim

ARG OPENRA_TAG=release-20250330
ARG OPENRA_APPIMAGE_FILE

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl wget xz-utils file \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/openra

# .NET Runtime
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates wget gnupg; \
    wget -O /tmp/packages-microsoft-prod.deb https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb; \
    dpkg -i /tmp/packages-microsoft-prod.deb; \
    rm -f /tmp/packages-microsoft-prod.deb; \
    apt-get update; \
    apt-get install -y --no-install-recommends dotnet-runtime-8.0; \
    rm -rf /var/lib/apt/lists/*

# Passende AppImage laden (pro Mod!)
RUN set -eux; \
    test -n "$OPENRA_APPIMAGE_FILE"; \
    url="https://github.com/OpenRA/OpenRA/releases/download/${OPENRA_TAG}/${OPENRA_APPIMAGE_FILE}"; \
    wget -O OpenRA.AppImage "$url"; \
    chmod +x OpenRA.AppImage

# AppImage extrahieren (kein FUSE)
RUN set -eux; \
    ./OpenRA.AppImage --appimage-extract; \
    mv squashfs-root /opt/openra/app; \
    rm -f OpenRA.AppImage

WORKDIR /opt/openra/app

ENTRYPOINT ["dotnet", "/opt/openra/app/usr/lib/openra/OpenRA.Server.dll"]
