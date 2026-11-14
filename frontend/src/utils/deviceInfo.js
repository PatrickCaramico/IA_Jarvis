// V7.6: nome e tipo do aparelho que pede a chave ao PC (aparece em Configurações > Segurança).
export function deviceInfo(ua = typeof navigator !== "undefined" ? navigator.userAgent : "") {
  const app = /JarvisApp/i.test(ua);
  const tv = /SmartTV|SMART-TV|BRAVIA|AFT\w|GoogleTV|Android TV|Tizen|Web0S|webOS/i.test(ua);
  const ipad = /iPad/i.test(ua) || (/Macintosh/i.test(ua) && /Mobile/i.test(ua));
  const android = /Android/i.test(ua);
  const tablet = ipad || (android && !/Mobile/i.test(ua) && !tv);
  const phone = !tablet && !tv && /Mobile|iPhone|Android/i.test(ua);
  const model = (ua.match(/Android [\d.]+; ([^;)]+?)(?: Build|\))/) || [])[1]?.trim();
  const kind = tv ? "tv" : tablet ? "tablet" : phone ? "celular" : "pc";
  let name;
  if (/iPhone/i.test(ua)) name = "iPhone";
  else if (ipad) name = "iPad";
  else if (android) name = model && model !== "K" ? model : kind === "tablet" ? "Tablet Android" : "Celular Android";
  else if (/Windows/i.test(ua)) name = "Computador Windows";
  else if (/Mac OS X/i.test(ua)) name = "Mac";
  else if (/Linux/i.test(ua)) name = "Computador Linux";
  else name = "Aparelho";
  if (tv) name = "TV";
  return { name: `${name}${app ? " (app JARVIS)" : ""}`.slice(0, 60), kind };
}
