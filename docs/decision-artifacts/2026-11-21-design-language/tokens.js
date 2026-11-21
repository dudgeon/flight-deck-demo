// Proposal token sets. The "before" set reproduces today's values; "after" is
// the proposed Product Aviator system. Option overrides layer on top.
window.PA_TOKENS = {
  before: {
    light: {
      // app chrome (upstream Omnigent palette)
      "app-bg": "#ffffff", "app-sidebar": "#f9f9f9", "app-sidebar-ink": "#27272a", "app-sidebar-ink-2": "#71717a",
      "app-active": "#fbe2ee", "app-active-ink": "#df3c85", "app-line": "#e4e4e7", "app-ink": "#27272a",
      "app-ink-2": "#71717a", "app-primary": "#11171c", "app-on-primary": "#ffffff", "app-header": "#ffffff",
      "app-header-ink": "#27272a", "app-bubble": "#f2f1f2", "app-canvas": "#f3f5f8", "app-logo": "#0a223d",
      // view kit (today)
      "pa-bg": "#f3f5f8", "pa-surface": "#ffffff", "pa-sunk": "#e9edf2", "pa-ink": "#0a223d", "pa-ink-2": "#44566c",
      "pa-ink-3": "#77879a", "pa-line": "#d3dae3", "pa-navy": "#0a223d", "pa-on-navy": "#f3f5f8",
      "pa-you": "#c2501f", "pa-you-soft": "#fbe6dc", "pa-ok": "#1d7a4f", "pa-ok-soft": "#dcf0e6",
      "pa-info": "#2f5d8a", "pa-info-soft": "#dfe9f3", "pa-warn": "#8a6200", "pa-warn-soft": "#f6ecd0",
      "pa-attn": "#b8323c", "pa-attn-soft": "#f8dfe1", "pa-idle": "#77879a", "pa-idle-soft": "#e9edf2",
      // templates (today)
      "tpl-bg": "#ffffff", "tpl-fg": "#1d1d1f", "tpl-muted": "#6e6e73", "tpl-line": "#e5e5ea", "tpl-card": "#f7f7f8",
      "tpl-accent": "#2f6feb", "tpl-win": "#e8f0fe"
    },
    dark: {
      "app-bg": "#18181b", "app-sidebar": "#141416", "app-sidebar-ink": "#e4e4e7", "app-sidebar-ink-2": "#a1a1aa",
      "app-active": "#3a1d2b", "app-active-ink": "#f06aa6", "app-line": "#2e2e33", "app-ink": "#e4e4e7",
      "app-ink-2": "#a1a1aa", "app-primary": "#f4f4f5", "app-on-primary": "#11171c", "app-header": "#18181b",
      "app-header-ink": "#e4e4e7", "app-bubble": "#27272a", "app-canvas": "#07172a", "app-logo": "#f2f4f7",
      "pa-bg": "#07172a", "pa-surface": "#0e2238", "pa-sunk": "#0a1c30", "pa-ink": "#e8eef5", "pa-ink-2": "#a9b8c9",
      "pa-ink-3": "#74879c", "pa-line": "#22384f", "pa-navy": "#2a5c94", "pa-on-navy": "#f3f7fb",
      "pa-you": "#ff9166", "pa-you-soft": "#3a2118", "pa-ok": "#5fcf98", "pa-ok-soft": "#0f3324",
      "pa-info": "#8fbbe6", "pa-info-soft": "#15304c", "pa-warn": "#e6bd55", "pa-warn-soft": "#35290c",
      "pa-attn": "#ff7d86", "pa-attn-soft": "#3b171b", "pa-idle": "#74879c", "pa-idle-soft": "#14283d",
      "tpl-bg": "#141414", "tpl-fg": "#f2f2f2", "tpl-muted": "#a1a1a6", "tpl-line": "#2c2c2e", "tpl-card": "#1d1d1f",
      "tpl-accent": "#6ea0ff", "tpl-win": "#1c2a44"
    }
  },
  after: {
    light: {
      "pa-bg": "#f4f6f9", "pa-surface": "#ffffff", "pa-sunk": "#eaeef3", "pa-ink": "#0f1e30", "pa-ink-2": "#475a70",
      "pa-ink-3": "#71829a", "pa-line": "#d6dde6", "pa-navy": "#0a223d", "pa-navy-2": "#17385f", "pa-navy-3": "#2a5486",
      "pa-on-navy": "#f2f6fa", "pa-on-navy-2": "#9fb4cc",
      "pa-you": "#b0237a", "pa-you-soft": "#f8e1ef",
      "pa-ok": "#17794a", "pa-ok-soft": "#ddf1e6", "pa-info": "#1e6aa6", "pa-info-soft": "#ddebf7",
      "pa-warn": "#8d5a00", "pa-warn-soft": "#f9ebcf", "pa-attn": "#8d5a00", "pa-attn-soft": "#f9ebcf",
      "pa-fail": "#b3261e", "pa-fail-soft": "#f9dedc", "pa-idle": "#71829a", "pa-idle-soft": "#eaeef3",
      "pa-agent": "#4f46b8"
    },
    dark: {
      "pa-bg": "#071526", "pa-surface": "#0c1e33", "pa-sunk": "#091a2d", "pa-ink": "#e6edf5", "pa-ink-2": "#a6b6c8",
      "pa-ink-3": "#71849a", "pa-line": "#1e3550", "pa-navy": "#2f64a0", "pa-navy-2": "#0d2138", "pa-navy-3": "#1a3a60",
      "pa-on-navy": "#f2f6fa", "pa-on-navy-2": "#8ea6c2",
      "pa-you": "#f26dc3", "pa-you-soft": "#3a1530",
      "pa-ok": "#5bcb93", "pa-ok-soft": "#0f3123", "pa-info": "#7db7ea", "pa-info-soft": "#12304d",
      "pa-warn": "#e9b44c", "pa-warn-soft": "#362808", "pa-attn": "#e9b44c", "pa-attn-soft": "#362808",
      "pa-fail": "#ff8a80", "pa-fail-soft": "#3d1715", "pa-idle": "#71849a", "pa-idle-soft": "#12263b",
      "pa-agent": "#a59cff"
    }
  },
  // option overrides on top of "after"
  you: {
    magenta: {},
    rust: { light: { "pa-you": "#c2501f", "pa-you-soft": "#fbe6dc" }, dark: { "pa-you": "#ff9166", "pa-you-soft": "#3a2118" } }
  },
  attn: {
    amber: {},
    red: { light: { "pa-attn": "#b3261e", "pa-attn-soft": "#f9dedc" }, dark: { "pa-attn": "#ff8a80", "pa-attn-soft": "#3d1715" } }
  }
};
