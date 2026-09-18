/**
 * What the contact sheet does inside the browser (doc 95): read a screenshot's
 * pixels, lay the cells out as one sheet, and time a render.
 *
 * Pixels are hashed from the decoded RGBA, never from the PNG file: a new PNG
 * encoder must not read as a change in the plan, and a changed pixel must.
 */

/** SHA-256 of a PNG's RGBA pixels, computed in the page. */
export async function pixelHash(page, png) {
  return page.evaluate(async (base64) => {
    const bytes = Uint8Array.from(atob(base64), (c) => c.charCodeAt(0));
    const bitmap = await createImageBitmap(new Blob([bytes], { type: 'image/png' }));
    const canvas = new OffscreenCanvas(bitmap.width, bitmap.height);
    const context = canvas.getContext('2d');
    context.drawImage(bitmap, 0, 0);
    const { data } = context.getImageData(0, 0, bitmap.width, bitmap.height);
    const digest = await crypto.subtle.digest('SHA-256', data);
    return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('');
  }, png.toString('base64'));
}

const escape = (text) => text.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);

/** Every cell on one page, rows by garden and columns by zoom, and a screenshot of it. */
export async function composeSheet(page, { mode, rows, columns }) {
  const ink = mode === 'dark' ? '#e8e6df' : '#2b2f28';
  const paper = mode === 'dark' ? '#1c1d1a' : '#f6f4ee';
  const head = columns.map((c) => `<th>${escape(c.label)}</th>`).join('');
  const body = rows.map((row) => {
    const cells = row.cells.map((cell) => `<td><img alt="" src="data:image/png;base64,${cell.png.toString('base64')}"></td>`);
    return `<tr><th>${escape(row.title)}</th>${cells.join('')}</tr>`;
  }).join('');
  await page.setViewportSize({ width: 1700, height: 1000 });
  await page.setContent(`<!doctype html><html lang="de"><head><meta charset="utf-8"><style>
    body { margin: 16px; background: ${paper}; color: ${ink}; font: 13px/1.3 system-ui, sans-serif; }
    table { border-collapse: separate; border-spacing: 12px 10px; }
    th { font-weight: 600; text-align: left; vertical-align: top; }
    img { display: block; }
  </style></head><body><table><tr><th></th>${head}</tr>${body}</table></body></html>`);
  return page.screenshot({ fullPage: true });
}

/** How long the last cell took from mounting its scene to its second painted frame. */
export async function paintMs(page) {
  return page.evaluate(() => window.paintMs);
}
