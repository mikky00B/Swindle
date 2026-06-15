import { toPng } from "html-to-image";

export async function exportElementAsPng(element: HTMLElement, fileName: string): Promise<void> {
  const dataUrl = await toPng(element, {
    cacheBust: true,
    pixelRatio: 2,
    width: 1080,
    height: 1080,
    style: {
      width: "1080px",
      height: "1080px",
    },
  });
  const link = document.createElement("a");
  link.download = fileName;
  link.href = dataUrl;
  link.click();
}
