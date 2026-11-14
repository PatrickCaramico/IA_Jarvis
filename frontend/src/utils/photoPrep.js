// V7.8: prepara a foto ANTES de sair do aparelho: reduz (no máximo 1600 px) e regrava em JPEG.
// Regravar pelo canvas apaga a localização (GPS) e os outros dados escondidos da foto (EXIF).
export const MAX_SIDE = 1600;
export const MAX_SOURCE_BYTES = 30 * 1024 * 1024;
const IMAGE_EXT = /\.(jpe?g|png|webp|gif|bmp|heic|heif|avif)$/i;

export function isImageFile(file) {
  return Boolean(file) && ((file.type || "").startsWith("image/") || IMAGE_EXT.test(file.name || ""));
}

export function fitSize(w, h, max = MAX_SIDE) {
  const scale = Math.min(1, max / Math.max(w, h || 1));
  return { width: Math.max(1, Math.round(w * scale)), height: Math.max(1, Math.round(h * scale)) };
}

async function decode(file) {
  if (typeof createImageBitmap === "function") {
    try {
      return await createImageBitmap(file, { imageOrientation: "from-image" });
    } catch {
      /* cai no <img> */
    }
  }
  const url = URL.createObjectURL(file);
  try {
    const img = new Image();
    img.src = url;
    await img.decode();
    return img;
  } finally {
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
}

export async function prepPhoto(file) {
  if (!isImageFile(file)) throw new Error("Isso não é uma imagem. Escolha uma foto (JPG, PNG ou WEBP).");
  if (file.size > MAX_SOURCE_BYTES) throw new Error("A foto é grande demais (mais de 30 MB).");
  let bmp;
  try {
    bmp = await decode(file);
  } catch {
    throw new Error("Não consegui abrir essa foto. Se for HEIC (iPhone), envie como JPG ou tire uma captura de tela dela.");
  }
  const { width, height } = fitSize(bmp.width, bmp.height);
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  canvas.getContext("2d").drawImage(bmp, 0, 0, width, height);
  bmp.close?.();
  const dataUrl = canvas.toDataURL("image/jpeg", 0.85);
  return { dataUrl, width, height };
}
