/* ============================================================
   САЙТ КОНТЕНТІ — бұл файлды АДМИН-ПАНЕЛЬ автоматты жасайды.
   Қолмен өзгертпеңіз: portfolio/admin/ сайтындағы админ-панельден
   өзгертіңіз (http://127.0.0.1:8138/admin).
   ============================================================ */

const CASE_FILES = [
  { src: 'bastau/аст 2-1.mp4', poster: 'posters/bastau/аст 2-1.mp4.png' },
  { src: 'bastau/asmr.mp4', poster: 'posters/bastau/asmr.mp4.png' },
  { src: 'bastau/B4(2) - 1 .mp4', poster: 'posters/bastau/B4(2) - 1 .mp4.png' },
  { src: 'Sham/шам таргет рус.mp4', poster: 'posters/Sham/шам таргет рус.mp4.png' },
  { src: 'Sham/шам таргет - 3 - 2 .mp4', poster: 'posters/Sham/шам таргет - 3 - 2 .mp4.png' },
  { src: 'Sham/студд-.mp4', poster: 'posters/Sham/студд-.mp4.png' },
  { src: 'Envy/0531.mp4', poster: 'posters/Envy/0531.mp4.png' },
  { src: 'Envy/envy y .mp4', poster: 'posters/Envy/envy y .mp4.png' },
  { src: 'Envy/envy creo1.mp4', poster: 'posters/Envy/envy creo1.mp4.png' },
  { src: 'Envy/envy 2 2- +.mp4', poster: 'posters/Envy/envy 2 2- +.mp4.png' },
  { src: 'Envy/envy 3 - +.mp4', poster: 'posters/Envy/envy 3 - +.mp4.png' },
  { src: 'Envy/sham 1.mp4', poster: 'posters/Envy/sham 1.mp4.png' },
  { src: 'Envy/4 lok.mp4', poster: 'posters/Envy/4 lok.mp4.png' },
  { src: 'Envy/zall.mp4', poster: 'posters/Envy/zall.mp4.png' }
];

window.PORTFOLIO_DATA = {
  "defaultLang": "kk",
  "contacts": {
    "email": "",
    "phone": "+7 776 921-86-32",
    "phoneHref": "+77769218632",
    "telegram": "miraskhmt",
    "telegramHref": "https://t.me/miraskhmt",
    "instagram": "miraskhmt",
    "instagramHref": "https://www.instagram.com/miraskhmt/"
  },
  "companies": [
    {
      "name": "ХБМ (kzchemistry)",
      "href": "https://www.instagram.com/kzchemistry/"
    },
    {
      "name": "Сая Қыдырәлі",
      "href": "https://www.instagram.com/saya.kidirali/"
    },
    {
      "name": "Envy studios",
      "href": "https://www.instagram.com/envy.studios/"
    },
    {
      "name": "Sham studio",
      "href": "https://www.instagram.com/shamstudio.kz/"
    },
    {
      "name": "Rent car Almaty",
      "href": "https://www.instagram.com/rentcaralmaty/"
    },
    {
      "name": "Bastau Brand",
      "href": "https://www.instagram.com/bastau.brand/"
    },
    {
      "name": "Study Point",
      "href": "https://www.instagram.com/studypoint_kz/"
    },
    {
      "name": "Astabaq",
      "href": "https://www.instagram.com/astabaq.kz/"
    },
    {
      "name": "Sevalo.kz",
      "href": "https://www.instagram.com/sevalo.kz/"
    }
  ],
  "languages": {
    "kk": {
      "ui": {
        "nav": {
          "cases": "Кейстер",
          "services": "Қызметтер",
          "about": "Мен жайлы",
          "contact": "Байланыс"
        },
        "heroBadge": "Жаңа жобаларға ашық",
        "ctaCases": "Кейстерді қарау",
        "ctaContact": "Хабарласу",
        "secCases": "Кейстер",
        "secServices": "Қызметтер",
        "secAbout": "Мен жайлы",
        "secContact": "Хабарласу",
        "secYears": "2022 — 2025",
        "phone": "Телефон",
        "telegram": "Telegram",
        "instagram": "Instagram",
        "footerRights": "Барлық құқықтар қорғалған",
        "footerTop": "Жоғарыға ↑",
        "casesNote": "Сыпырып көріңіз — видео басқанда ашылады.",
        "videosWord": "видео",
        "openVideo": "Видео ашу"
      },
      "meta": {
        "name": "Мирас Хамитов",
        "role": "Видеограф / Монтажёр",
        "tagline": "Кадр арқылы оқиға айтамын",
        "intro": "Мен видеограф және монтажёрмын: түсірілім, монтаж, түс-коррекция және брендтерге арналған видеоконтент. Әр кадр мағыналы болуы керек — қарапайым, бірақ кәсіби.",
        "location": "Алматы, Қазақстан",
        "availability": "Жаңа жобаларға ашық"
      },
      "cases": [],
      "services": [
        {
          "title": "Видео түсірілім",
          "desc": "Бренд-видео, клип, іс-шара, Reels — кәсіби құрылғылармен түсірілім."
        },
        {
          "title": "Монтаж & постпродакшн",
          "desc": "Монтаж, түс-коррекция, саунд-дизайн және анимациялық тайтлдар."
        },
        {
          "title": "Контент-видео",
          "desc": "Әлеуметтік желілерге арналған тұрақты видеоконтент: Reels, Shorts, Stories."
        }
      ],
      "stats": [
        {
          "value": "3+",
          "label": "Жыл тәжірибе"
        },
        {
          "value": "100+",
          "label": "Түсірілген видео"
        },
        {
          "value": "9+",
          "label": "Серіктес компания"
        }
      ]
    },
    "ru": {
      "ui": {
        "nav": {
          "cases": "Кейсы",
          "services": "Услуги",
          "about": "Обо мне",
          "contact": "Контакты"
        },
        "heroBadge": "Открыт к новым проектам",
        "ctaCases": "Смотреть кейсы",
        "ctaContact": "Связаться",
        "secCases": "Кейсы",
        "secServices": "Услуги",
        "secAbout": "Обо мне",
        "secContact": "Связаться",
        "secYears": "2022 — 2025",
        "phone": "Телефон",
        "telegram": "Telegram",
        "instagram": "Instagram",
        "footerRights": "Все права защищены",
        "footerTop": "Наверх ↑",
        "casesNote": "Листайте — видео откроется по клику.",
        "videosWord": "видео",
        "openVideo": "Открыть видео"
      },
      "meta": {
        "name": "Мирас Хамитов",
        "role": "Видеограф / Монтажёр",
        "tagline": "Рассказываю истории через кадр",
        "intro": "Я видеограф и монтажёр: съёмка, монтаж, цветокоррекция и видеоконтент для брендов. Каждый кадр должен быть осмысленным — просто, но профессионально.",
        "location": "Алматы, Казахстан",
        "availability": "Открыт к новым проектам"
      },
      "cases": [],
      "services": [
        {
          "title": "Видеосъёмка",
          "desc": "Бренд-видео, клипы, мероприятия, Reels — профессиональное оборудование."
        },
        {
          "title": "Монтаж & постпродакшн",
          "desc": "Монтаж, цветокоррекция, саунд-дизайн и анимированные титры."
        },
        {
          "title": "Контент-видео",
          "desc": "Регулярный видеоконтент для соцсетей: Reels, Shorts, Stories."
        }
      ],
      "stats": [
        {
          "value": "3+",
          "label": "Лет опыта"
        },
        {
          "value": "100+",
          "label": "Снятых видео"
        },
        {
          "value": "9+",
          "label": "Компаний-партнёров"
        }
      ]
    },
    "en": {
      "ui": {
        "nav": {
          "cases": "Cases",
          "services": "Services",
          "about": "About me",
          "contact": "Contact"
        },
        "heroBadge": "Open to new projects",
        "ctaCases": "View cases",
        "ctaContact": "Get in touch",
        "secCases": "Cases",
        "secServices": "Services",
        "secAbout": "About me",
        "secContact": "Contact",
        "secYears": "2022 — 2025",
        "phone": "Phone",
        "telegram": "Telegram",
        "instagram": "Instagram",
        "footerRights": "All rights reserved",
        "footerTop": "Back to top ↑",
        "casesNote": "Swipe through — click a video to open it.",
        "videosWord": "videos",
        "openVideo": "Open video"
      },
      "meta": {
        "name": "Miras Khamitov",
        "role": "Videographer / Video Editor",
        "tagline": "I tell stories through the frame",
        "intro": "I'm a videographer and video editor: shooting, editing, color grading and video content for brands. Every frame should be meaningful — simple, yet professional.",
        "location": "Almaty, Kazakhstan",
        "availability": "Open to new projects"
      },
      "cases": [],
      "services": [
        {
          "title": "Video production",
          "desc": "Brand videos, music clips, events, Reels — shot with professional gear."
        },
        {
          "title": "Editing & post-production",
          "desc": "Editing, color grading, sound design and animated titles."
        },
        {
          "title": "Content video",
          "desc": "Ongoing video content for social media: Reels, Shorts, Stories."
        }
      ],
      "stats": [
        {
          "value": "3+",
          "label": "Years of experience"
        },
        {
          "value": "100+",
          "label": "Videos produced"
        },
        {
          "value": "9+",
          "label": "Partner companies"
        }
      ]
    }
  }
};
window.PORTFOLIO_DATA.trackApi = 'https://expects-phillips-reconstruction-locale.trycloudflare.com';

(function () {
  const D = window.PORTFOLIO_DATA;
  const titleOf = (src) =>
    src.split("/").pop().replace(/\.(mp4|mov|webm)$/i, "").trim();
  for (const lang in D.languages) {
    D.languages[lang].cases = CASE_FILES.map((f) => ({
      title: titleOf(f.src),
      tags: [],
      year: "",
      media: [{ type: "video", src: f.src, poster: f.poster || "" }]
    }));
  }
})();
