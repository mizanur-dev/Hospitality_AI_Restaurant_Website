# 🎨 Hospitality AI - Design System

## Brand Identity

**Mission:** Help restaurant owners make data-driven decisions with confidence

**Visual Style:** Modern, colorful, approachable yet professional

**Target Users:** Restaurant owners (non-technical), consultants

---

## 🎨 Color Palette

### Primary Colors
```css
/* Brand Primary - Trust & Innovation */
--indigo-600: #4f46e5;  /* Buttons, links, primary actions */
--indigo-700: #4338ca;  /* Hover states */
--indigo-50: #eef2ff;   /* Backgrounds, subtle highlights */

/* Brand Secondary - Success & Growth */
--emerald-600: #059669; /* Success states, positive metrics */
--emerald-50: #ecfdf5;  /* Success backgrounds */
```

### Semantic Colors
```css
/* Performance Indicators */
--success: #10b981;     /* ✅ Good - On target (Green) */
--warning: #f59e0b;     /* ⚠️  Watch - Near limit (Amber) */
--danger: #ef4444;      /* 🚨 Alert - Over limit (Red) */
--info: #3b82f6;        /* ℹ️  Info - Insights (Blue) */

/* Financial Colors */
--revenue: #059669;     /* Income, sales (Green) */
--cost: #dc2626;        /* Expenses, costs (Red) */
--profit: #8b5cf6;      /* Profit, margin (Purple) */

/* Neutral Colors */
--gray-50: #f9fafb;     /* Backgrounds */
--gray-100: #f3f4f6;    /* Subtle backgrounds */
--gray-500: #6b7280;    /* Secondary text */
--gray-900: #111827;    /* Primary text */
--white: #ffffff;       /* Cards, surfaces */
```

### Usage Rules
- 🟢 **Green:** KPIs on target, positive trends
- 🟡 **Amber:** KPIs approaching limits, needs attention
- 🔴 **Red:** KPIs over limits, urgent action needed
- 🔵 **Blue:** Informational, neutral data
- 🟣 **Purple:** Special insights, premium features

---

## 📝 Typography

### Font Stack
```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto',
             'Helvetica Neue', Arial, sans-serif;
```

### Text Hierarchy

**Page Titles:**
```css
font-size: 2.25rem;     /* 36px */
font-weight: 800;       /* Extra Bold */
line-height: 1.2;
color: var(--gray-900);
```

**Section Headers:**
```css
font-size: 1.5rem;      /* 24px */
font-weight: 700;       /* Bold */
line-height: 1.3;
color: var(--gray-900);
```

**Card Titles:**
```css
font-size: 1.125rem;    /* 18px */
font-weight: 600;       /* Semi-bold */
line-height: 1.4;
color: var(--gray-900);
```

**Body Text:**
```css
font-size: 1rem;        /* 16px */
font-weight: 400;       /* Regular */
line-height: 1.5;
color: var(--gray-700);
```

**Small Text:**
```css
font-size: 0.875rem;    /* 14px */
font-weight: 500;       /* Medium */
line-height: 1.4;
color: var(--gray-500);
```

**Big Numbers (KPIs):**
```css
font-size: 2.5rem;      /* 40px */
font-weight: 700;       /* Bold */
line-height: 1;
letter-spacing: -0.02em;
```

---

## 📏 Spacing System

Use multiples of 4px for consistency:

```
4px   = 0.25rem  (xs)  - Tight spacing
8px   = 0.5rem   (sm)  - Small gaps
12px  = 0.75rem  (md)  - Medium gaps
16px  = 1rem     (base)- Standard padding
24px  = 1.5rem   (lg)  - Card padding
32px  = 2rem     (xl)  - Section spacing
48px  = 3rem     (2xl) - Large spacing
64px  = 4rem     (3xl) - Page margins
```

---

## 🎭 Components

### Cards
```css
background: white;
border-radius: 1rem;        /* 16px */
padding: 1.5rem;            /* 24px */
box-shadow: 0 1px 3px rgba(0,0,0,0.1);
border: 1px solid #f3f4f6;
```

**Hover State:**
```css
transform: translateY(-4px);
box-shadow: 0 12px 24px rgba(0,0,0,0.12);
transition: all 0.3s ease;
```

### Buttons

**Primary Button:**
```css
background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%);
color: white;
padding: 0.75rem 1.5rem;
border-radius: 0.75rem;
font-weight: 600;
box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
```

**Secondary Button:**
```css
background: white;
color: #4f46e5;
border: 2px solid #4f46e5;
padding: 0.75rem 1.5rem;
border-radius: 0.75rem;
font-weight: 600;
```

### Badges

**Good Status:**

<span class="px-3 py-1 bg-emerald-100 text-emerald-800 rounded-full text-sm font-semibold">
  ✓ On Target
</span>
```

**Warning Status:**

<span class="px-3 py-1 bg-amber-100 text-amber-800 rounded-full text-sm font-semibold">
  ⚠ Watch
</span>
```

**Alert Status:**

<span class="px-3 py-1 bg-red-100 text-red-800 rounded-full text-sm font-semibold">
  ⚠️ Alert
</span>
```

---

## 📊 Data Visualization

### Chart Colors
Use these colors consistently across all charts:

**Sales/Revenue:**
```css
primary: #10b981 (emerald-600)
light: rgba(16, 185, 129, 0.1)
```

**Costs/Expenses:**
```css
primary: #ef4444 (red-500)
light: rgba(239, 68, 68, 0.1)
```

**Labor:**
```css
primary: #f59e0b (amber-500)
light: rgba(245, 158, 11, 0.1)
```

**Food Cost:**
```css
primary: #fb923c (orange-400)
light: rgba(251, 146, 60, 0.1)
```

**Profit:**
```css
primary: #8b5cf6 (purple-500)
light: rgba(139, 92, 246, 0.1)
```

### Chart Style Guidelines
- Use smooth curves (`tension: 0.4`)
- Show data labels on hover only
- Use shadows for depth
- Animate on load
- Keep gridlines subtle (`rgba(0,0,0,0.05)`)

---

## 🎬 Animations

### Timing
```css
/* Fast interactions */
.fast { transition: all 0.15s ease; }

/* Standard interactions */
.standard { transition: all 0.3s ease; }

/* Slow, emphasis */
.slow { transition: all 0.5s ease; }
```

### Common Animations

**Slide Up (Cards on load):**
```css
@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

**Fade In:**
```css
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
```

**Pulse (Live indicators):**
```css
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
```

---

## 📱 Responsive Design

### Breakpoints
```css
/* Mobile First Approach */
sm: 640px   /* Small tablets */
md: 768px   /* Tablets */
lg: 1024px  /* Laptops */
xl: 1280px  /* Desktops */
2xl: 1536px /* Large screens */
```

### Mobile Considerations
- Touch targets: minimum 44x44px
- Larger text on mobile (16px minimum)
- Simplified navigation (hamburger menu)
- Single column layouts on mobile
- Swipeable cards
- Bottom navigation for key actions

---

## 🎯 KPI Display Guidelines

### Traffic Light System
```
🟢 Good:    ≤ Target (Green)
🟡 Warning: 90-100% of target (Amber)
🔴 Alert:   > Target (Red)
```

### Number Formatting
```javascript
// Currency
$45,230 (not $45230.00)

// Percentages
28.3% (one decimal)

// Large numbers
$1.2M (not $1,200,000)
```

### Trend Indicators
```
↑ +12.5% (green) - Positive trend
↓ -5.2% (red)    - Negative trend
→ 0.0% (gray)    - No change
```

---

## 🎨 Layout Templates

### Dashboard Layout
```
┌─────────────────────────────────────┐
│  Header (Logo, Nav, Actions)        │
├─────────────────────────────────────┤
│  Hero Section (Welcome, CTA)        │
├─────────────────────────────────────┤
│  ┌──────┐ ┌──────┐ ┌──────┐        │
│  │ KPI  │ │ KPI  │ │ KPI  │        │
│  └──────┘ └──────┘ └──────┘        │
├─────────────────────────────────────┤
│  ┌────────────┐  ┌────────────┐    │
│  │  Chart 1   │  │  Chart 2   │    │
│  └────────────┘  └────────────┘    │
├─────────────────────────────────────┤
│  Data Table                         │
└─────────────────────────────────────┘
```

---

## ✅ Checklist for Polished Pages

Every page should have:
- [ ] Consistent header with logo and navigation
- [ ] Clear page title and description
- [ ] Color-coded KPI cards
- [ ] Interactive charts with animations
- [ ] Mobile-responsive layout
- [ ] Loading states (spinners)
- [ ] Empty states (when no data)
- [ ] Error states (when something fails)
- [ ] Export functionality (PDF/CSV)
- [ ] Help tooltips for complex metrics
- [ ] Consistent spacing (using spacing system)
- [ ] Smooth animations on interactions
- [ ] Accessible (ARIA labels, keyboard navigation)

---

## 🚫 Don'ts

❌ **Don't use:**
- Comic Sans or decorative fonts
- More than 3 colors in a single chart
- Tiny text (< 14px on mobile)
- Cluttered layouts with too much data
- Jarring animations or transitions
- Inconsistent spacing
- Low-contrast text
- Overly technical jargon

✅ **Do use:**
- Simple, clear language
- Plenty of white space
- Visual hierarchy (size, color, spacing)
- Consistent patterns
- Loading states
- Helpful empty states

---

## 📚 Resources

**Icons:**
- Lucide Icons: https://lucide.dev/
- Heroicons: https://heroicons.com/

**Colors:**
- Tailwind Color Palette: https://tailwindcss.com/docs/customizing-colors

**Charts:**
- Chart.js: https://www.chartjs.org/

**Components:**
- Tailwind UI: https://tailwindui.com/ (Premium)
- Headless UI: https://headlessui.com/ (Free)

---

**Last Updated:** October 2025
**Version:** 1.0
