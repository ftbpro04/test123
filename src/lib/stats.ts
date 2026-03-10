export const tokenEstimate = (text: string) => Math.ceil(text.trim().length / 4);
export const wordCount = (text: string) => (text.trim() ? text.trim().split(/\s+/).length : 0);
