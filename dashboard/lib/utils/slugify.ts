/**
 * Convert a string to a URL-friendly slug
 * @param str - The string to slugify
 * @returns The slugified string
 */
export const slugify = (str: string): string => {
  return str
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-+|-+$/g, "");
};
