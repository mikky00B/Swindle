import type { ShareCardData } from "../types";

export function positionLabel(source: ShareCardData["board_position_source"]): string {
  if (source === "key_position") {
    return "Key position";
  }
  if (source === "fallback_starting_position") {
    return "Starting position fallback";
  }
  return "Final position";
}
