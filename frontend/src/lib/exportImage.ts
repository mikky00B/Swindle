import { toPng } from "html-to-image";

type ExportPngOptions = {
  width: number;
  height: number;
};

export async function exportElementAsPng(element: HTMLElement, fileName: string, options: ExportPngOptions): Promise<void> {
  const dataUrl = await toPng(element, {
    cacheBust: true,
    pixelRatio: 2,
    width: options.width,
    height: options.height,
    style: {
      width: `${options.width}px`,
      height: `${options.height}px`,
    },
  });
  const link = document.createElement("a");
  link.download = fileName;
  link.href = dataUrl;
  link.click();
}
