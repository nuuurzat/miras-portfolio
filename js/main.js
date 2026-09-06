/* ============================================================
   Сайт логикасы: 3 тілді шығару, кейс-видео, анимация, түс режимі.
   Контент content.js-те; осы файл — тек шығару логикасы.
   ============================================================ */

(function () {
  "use strict";

  const D = window.PORTFOLIO_DATA;
  const LANGS = D.languages;
  const C = D.contacts;

  let lang = localStorage.getItem("lang") || D.defaultLang;
  if (!LANGS[lang]) lang = D.defaultLang;
  const L = () => LANGS[lang];
  const ui = () => L().ui;

  /* ---------- Түс режимі (light / dark) ---------- */
  const root = document.documentElement;
  const stored = localStorage.getItem("theme");
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  root.dataset.theme = stored || (prefersDark ? "dark" : "light");

  document.getElementById("themeToggle").addEventListener("click", () => {
    root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
    localStorage.setItem("theme", root.dataset.theme);
  });

  /* ---------- Тіл ауыстырғыш ---------- */
  const langButtons = document.querySelectorAll(".lang-btn");
  langButtons.forEach((btn) =>
    btn.addEventListener("click", () => {
      if (btn.dataset.lang === lang) return;
      lang = btn.dataset.lang;
      localStorage.setItem("lang", lang);
      renderAll();
    })
  );

  /* ---------- Көмекші функциялар ---------- */
  const setText = (sel, val) => {
    document.querySelectorAll(sel).forEach((el) => (el.textContent = val));
  };
  const esc = (s) =>
    String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  const ic = (paths) =>
    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${paths}</svg>`;
  const playIcon =
    '<svg viewBox="0 0 24 24" fill="currentColor" stroke="none"><path d="M8 5v14l11-7z"/></svg>';

  /* ---------- Лайтбокс (кейс медиасы) ---------- */
  const lightbox = document.createElement("div");
  lightbox.className = "lightbox";
  lightbox.innerHTML = '<div class="lightbox-inner"></div>';
  document.body.appendChild(lightbox);

  const openMedia = (media) => {
    const inner = lightbox.querySelector(".lightbox-inner");
    inner.innerHTML = "";
    media.forEach((m) => {
      const src = `img/${m.src}`;
      const el =
        m.type === "video"
          ? Object.assign(document.createElement("video"), {
              src,
              poster: m.poster ? `img/${m.poster}` : undefined,
              controls: true,
              autoplay: true,
              playsInline: true,
            })
          : Object.assign(document.createElement("img"), { src, alt: "" });
      inner.appendChild(el);
    });
    lightbox.classList.add("open");
    document.body.style.overflow = "hidden";
  };
  const closeMedia = () => {
    lightbox.classList.remove("open");
    document.body.style.overflow = "";
    lightbox.querySelector("video")?.pause();
  };
  let dragLock = false;
  document.addEventListener("click", (e) => {
    if (dragLock) return;
    const reel = e.target.closest(".reel[data-media]");
    if (reel) {
      openMedia(JSON.parse(reel.dataset.media));
      return;
    }
    if (e.target === lightbox) closeMedia();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeMedia();
  });

  /* ---------- Шығару (render) ---------- */
  const renderAll = () => {
    const meta = L().meta;
    root.lang = lang;

    // Негізгі мәтіндер
    setText("[data-name]", meta.name);
    setText("[data-role]", meta.role);
    setText("[data-intro]", meta.intro);
    setText("[data-location]", meta.location);
    setText("[data-availability]", meta.availability);
    setText("[data-cases-count]", String(L().cases.length).padStart(2, "0"));
    setText("[data-year]", new Date().getFullYear());
    setText("[data-cases-note]", ui().casesNote || "");
    document.title = `${meta.name} — ${meta.role}`;

    // Интерфейс мәтіндері (data-i18n)
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const v = el.dataset.i18n.split(".").reduce((o, k) => (o ? o[k] : undefined), ui());
      if (v !== undefined) el.textContent = v;
    });

    // Үлкен контакт блогы: email жоқ болса — телефон
    const emailEl = document.querySelector("[data-email-link]");
    if (C.email) {
      emailEl.textContent = `${C.email} ↗`;
      emailEl.href = `mailto:${C.email}`;
    } else {
      emailEl.textContent = `${C.phone} ↗`;
      emailEl.href = `tel:${C.phoneHref}`;
    }

    // Контакт карточкалары
    const cards = [];
    if (C.phone)
      cards.push({
        label: ui().phone,
        value: C.phone,
        href: `tel:${C.phoneHref}`,
        icon: ic('<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>'),
      });
    if (C.telegram)
      cards.push({
        label: ui().telegram,
        value: C.telegram,
        href: C.telegramHref,
        icon: ic('<path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4z"/>'),
      });
    if (C.instagram)
      cards.push({
        label: ui().instagram,
        value: C.instagram,
        href: C.instagramHref,
        icon: ic('<rect x="2" y="2" width="20" height="20" rx="5"/><path d="M16 11.37a4 4 0 1 1-7.8-1.1A4 4 0 0 1 16 11.37z"/><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/>'),
      });
    document.querySelector("[data-contact]").innerHTML = cards
      .map(
        (c, i) =>
          `<a class="contact-card" data-reveal style="--d:${0.08 * i}s" href="${c.href}" target="_blank" rel="noopener">
            <span class="ic">${c.icon}</span>
            <span><small>${esc(c.label)}</small><strong>${esc(c.value)}</strong></span>
          </a>`
      )
      .join("");

    // Кейстер — релс-карусель: үлкен вертикаль карточкалар, бір қатар
    const enc = (p) => encodeURI(p);
    const emptyGrad = "linear-gradient(135deg,#2B2922 0%,#1A1915 100%)";
    const reelInner = (c) => {
      const first = (c.media || [])[0];
      if (first && first.type === "video") {
        return first.poster
          ? `<img src="${esc(enc("img/" + first.poster))}" alt="" loading="lazy" />`
          : `<video muted playsinline preload="metadata" src="${esc(enc("img/" + first.src))}"></video>`;
      }
      return "";
    };

    const casesEl = document.querySelector("[data-cases]");
    casesEl.innerHTML = (L().cases || [])
      .map((c, i) => {
        const media = c.media || [];
        return `<button type="button" class="reel" role="button" data-media="${esc(JSON.stringify(media))}" aria-label="${esc(ui().openVideo || "Видео")} ${i + 1}">
          <span class="reel-bg" style="background:${media.length ? "#000" : emptyGrad}">${reelInner(c)}</span>
          <span class="play-badge">${playIcon}</span>
        </button>`;
      })
      .join("");

    // --- Карусель: көлденең сыпыру (drag + wheel) ---
    let isDown = false, startX = 0, startLeft = 0, dragged = false;
    casesEl.addEventListener("pointerdown", (e) => {
      isDown = true;
      dragged = false;
      startX = e.clientX;
      startLeft = casesEl.scrollLeft;
      casesEl.classList.add("grabbing");
    });
    casesEl.addEventListener("pointermove", (e) => {
      if (!isDown) return;
      const dx = e.clientX - startX;
      if (Math.abs(dx) > 6) dragged = true;
      casesEl.scrollLeft = startLeft - dx;
    });
    ["pointerup", "pointercancel"].forEach((ev) =>
      casesEl.addEventListener(ev, () => {
        if (dragged) {
          dragLock = true;
          setTimeout(() => (dragLock = false), 120);
        }
        isDown = false;
        casesEl.classList.remove("grabbing");
        setTimeout(() => (dragged = false), 60);
      })
    );
    // Тік скролды көлденеңге айналдыру (релс сияқты жүреді)
    casesEl.addEventListener(
      "wheel",
      (e) => {
        if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
          casesEl.scrollLeft += e.deltaY;
          e.preventDefault();
        }
      },
      { passive: false }
    );

    // Қызметтер
    document.querySelector("[data-services]").innerHTML = (L().services || [])
      .map(
        (s, i) => `<div class="service" data-reveal style="--d:${0.08 * i}s">
          <span class="service-num">0${i + 1}</span>
          <h3>${esc(s.title)}</h3>
          <p>${esc(s.desc)}</p>
        </div>`
      )
      .join("");

    // Статистика
    document.querySelector("[data-stats]").innerHTML = (L().stats || [])
      .map(
        (s) => `<div class="stat">
          <strong>${esc(s.value)}</strong>
          <span>${esc(s.label)}</span>
        </div>`
      )
      .join("");

    // Компаниялар marquee
    const companyItem = (c) =>
      c.href
        ? `<a href="${esc(c.href)}" target="_blank" rel="noopener">${esc(c.name)}</a>`
        : `<span>${esc(c.name)}</span>`;
    const items = D.companies.map(companyItem).join("");
    document.querySelector("[data-marquee]").innerHTML = items + items;

    // Мен жайлы
    document.querySelector("[data-about]").innerHTML =
      esc(meta.intro) + " <em>" + esc(meta.tagline) + ".</em>";

    // Тіл батырмаларының белсендісі
    langButtons.forEach((b) => b.classList.toggle("active", b.dataset.lang === lang));

    // Reveal анимацияларын жаңа элементтерге қайта тіркеу
    observeAll();
  };

  /* ---------- Reveal анимация ---------- */
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add("in");
          io.unobserve(e.target);
        }
      });
    },
    { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
  );
  const observeAll = () => {
    document.querySelectorAll("[data-reveal]").forEach((el) => io.observe(el));
  };

  /* ---------- Header — скроллда сызық ---------- */
  const header = document.querySelector(".site-header");
  const onScroll = () => header.classList.toggle("scrolled", window.scrollY > 8);
  window.addEventListener("scroll", onScroll, { passive: true });

  renderAll();
  onScroll();
})();
