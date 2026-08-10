import { useEffect, useState } from "react";
import { apiClient } from "../api/client";

export function useProtectedAssetUrl(rawUrl: string): string {
  const [mediaUrl, setMediaUrl] = useState("");

  useEffect(() => {
    let active = true;
    let objectUrl = "";
    if (!rawUrl) {
      setMediaUrl("");
      return undefined;
    }
    if (!rawUrl.startsWith("/api/files/")) {
      setMediaUrl(rawUrl);
      return undefined;
    }
    apiClient.assetBlob(rawUrl)
      .then((blob) => {
        if (!active) {
          return;
        }
        objectUrl = URL.createObjectURL(blob);
        setMediaUrl(objectUrl);
      })
      .catch(() => {
        if (active) {
          setMediaUrl("");
        }
      });
    return () => {
      active = false;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [rawUrl]);

  return mediaUrl;
}

export function ProtectedImage({ src, alt }: { src: string; alt: string }) {
  const mediaUrl = useProtectedAssetUrl(src);
  return mediaUrl ? <img src={mediaUrl} alt={alt} /> : null;
}

export function ProtectedAssetPreview({ src, isVideo, alt }: { src: string; isVideo?: boolean; alt: string }) {
  const mediaUrl = useProtectedAssetUrl(src);
  if (!mediaUrl) {
    return null;
  }
  return isVideo
    ? <video src={mediaUrl} controls playsInline preload="metadata" />
    : <img src={mediaUrl} alt={alt} />;
}
