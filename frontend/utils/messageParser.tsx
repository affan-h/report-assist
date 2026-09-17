import { ReactNode } from "react";

// Regex to find strings like <<<my_file.png>>>
const IMAGE_REGEX = /<<<([^>]+)>>>/g;

export const parseMessageContent = (
  content: string,
  renderImage: (filename: string, index: number) => ReactNode
) => {
  // 1. Split the string by the regex
  const parts = content.split(IMAGE_REGEX);

  // 2. Map through parts.
  // The split logic with capturing groups works like this:
  // "Text <<<Image>>> Text" -> ["Text ", "Image", " Text"]
  // Even indices (0, 2, 4) are always TEXT
  // Odd indices (1, 3, 5) are always FILENAMES (captured by the group).

  return parts.map((part, index) => {
    if (index % 2 === 1) {
      // This is a filename (Odd index)
      return renderImage(part.trim(), index);
    } else {
      // This is text (Even index)
      if (!part.trim()) return null; // Skip empty whitespace
      return (
        <p key={index} className="mb-4 whitespace-pre-wrap leading-relaxed">
          {part}
        </p>
      );
    }
  });
};
