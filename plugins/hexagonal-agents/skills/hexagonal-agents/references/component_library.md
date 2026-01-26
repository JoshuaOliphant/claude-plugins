# UI Component Library

Complete reference for UI components in hexagonal agent applications. All components use Tailwind CSS and include HTMX attributes for interactivity.

---

## Design System

### Color Palette

```
Backgrounds:
- Page:       bg-slate-950
- Cards:      bg-slate-900
- Inputs:     bg-slate-800
- Highlight:  bg-slate-800/50
- Overlay:    bg-slate-950/80 backdrop-blur-sm

Borders:
- Default:    border-slate-800
- Emphasis:   border-slate-700
- Focus:      ring-2 ring-indigo-500

Primary Accent:
- Button:     bg-indigo-600 hover:bg-indigo-500
- Link:       text-indigo-400 hover:text-indigo-300
- Focus:      ring-indigo-500
- Glow:       shadow-indigo-500/25

Text:
- Heading:    text-white
- Body:       text-slate-300
- Muted:      text-slate-400
- Caption:    text-slate-500
- Success:    text-emerald-400
- Warning:    text-amber-400
- Danger:     text-red-400
```

### Typography

```
Headings:
- font-['Space_Grotesk'] (load via Google Fonts)

Sizes:
- Page title:    text-2xl font-bold
- Section title: text-xl font-semibold
- Card title:    text-lg font-medium
- Body:          text-base
- Small:         text-sm
- Caption:       text-xs
```

### Animation

```css
@keyframes fadeSlideIn {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
}
.animate-in { animation: fadeSlideIn 0.3s ease-out; }

/* Staggered reveals */
.stagger-1 { animation-delay: 0.05s; }
.stagger-2 { animation-delay: 0.1s; }
.stagger-3 { animation-delay: 0.15s; }
```

---

## Layout Components

### Page Header

```html
<div class="flex justify-between items-center mb-8 animate-in">
  <div>
    <h1 class="text-2xl font-bold font-['Space_Grotesk'] text-white">Page Title</h1>
    <p class="text-slate-400 mt-1">Supporting description text</p>
  </div>
  <button hx-post="/agent" hx-target="#content" hx-vals='{"message":"create new"}'
          class="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg
                 shadow-lg shadow-indigo-500/25 transition-all duration-200 hover:shadow-indigo-500/40">
    + New Item
  </button>
</div>
```

### Section Header

```html
<div class="flex items-center justify-between mb-4">
  <h2 class="text-xl font-semibold font-['Space_Grotesk'] text-white">Section Title</h2>
  <button hx-post="/agent" hx-target="#content" hx-vals='{"message":"action"}'
          class="text-sm text-indigo-400 hover:text-indigo-300 transition-colors">
    View All →
  </button>
</div>
```

### Card

```html
<div class="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden
            shadow-lg shadow-slate-950/50 animate-in">
  <div class="p-5">
    <!-- content -->
  </div>
</div>
```

### Card with Header

```html
<div class="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden shadow-lg shadow-slate-950/50">
  <div class="px-5 py-4 border-b border-slate-800 bg-slate-800/30">
    <h3 class="font-semibold text-white">Card Title</h3>
  </div>
  <div class="p-5">
    <!-- content -->
  </div>
</div>
```

### Card with Actions

```html
<div class="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden shadow-lg shadow-slate-950/50">
  <div class="px-5 py-4 border-b border-slate-800 bg-slate-800/30 flex justify-between items-center">
    <h3 class="font-semibold text-white">Card Title</h3>
    <div class="flex gap-2">
      <button hx-post="/agent" hx-target="#content" hx-vals='{"message":"edit"}'
              class="text-sm text-slate-400 hover:text-white transition-colors">Edit</button>
      <button hx-post="/agent" hx-target="#content" hx-vals='{"message":"delete"}'
              class="text-sm text-red-400 hover:text-red-300 transition-colors">Delete</button>
    </div>
  </div>
  <div class="p-5">
    <!-- content -->
  </div>
</div>
```

### Stats Grid

```html
<div class="grid grid-cols-3 gap-4 mb-8 animate-in">
  <div class="bg-slate-900 rounded-xl border border-slate-800 p-5">
    <p class="text-sm text-slate-400 mb-1">Total</p>
    <p class="text-3xl font-bold font-['Space_Grotesk'] text-white">24</p>
  </div>
  <div class="bg-slate-900 rounded-xl border border-slate-800 p-5">
    <p class="text-sm text-slate-400 mb-1">Active</p>
    <p class="text-3xl font-bold font-['Space_Grotesk'] text-emerald-400">18</p>
  </div>
  <div class="bg-slate-900 rounded-xl border border-slate-800 p-5">
    <p class="text-sm text-slate-400 mb-1">Completed</p>
    <p class="text-3xl font-bold font-['Space_Grotesk'] text-slate-400">6</p>
  </div>
</div>
```

---

## List Components

### Interactive List Item

```html
<div class="group flex items-center justify-between p-4 bg-slate-900 rounded-lg border border-slate-800
            hover:border-slate-700 hover:bg-slate-800/50 transition-all duration-200 cursor-pointer animate-in"
     hx-post="/agent" hx-target="#content" hx-vals='{"message":"show item 123"}'>
  <div class="flex items-center gap-4">
    <div class="w-10 h-10 rounded-lg bg-indigo-600/20 flex items-center justify-center">
      <span class="text-indigo-400 font-semibold">A</span>
    </div>
    <div>
      <p class="font-medium text-white group-hover:text-indigo-300 transition-colors">Item Name</p>
      <p class="text-sm text-slate-400">Description or metadata</p>
    </div>
  </div>
  <div class="text-slate-400 group-hover:text-white transition-colors">→</div>
</div>
```

### List Item with Actions

```html
<div class="flex items-center justify-between p-4 bg-slate-900 rounded-lg border border-slate-800">
  <div class="flex items-center gap-4">
    <div class="w-10 h-10 rounded-lg bg-indigo-600/20 flex items-center justify-center">
      <span class="text-indigo-400 font-semibold">A</span>
    </div>
    <div>
      <p class="font-medium text-white">Item Name</p>
      <p class="text-sm text-slate-400">Description</p>
    </div>
  </div>
  <div class="flex items-center gap-2">
    <button hx-post="/agent" hx-target="#content" hx-vals='{"message":"edit item 123"}'
            class="px-3 py-1.5 text-sm text-slate-400 hover:text-white hover:bg-slate-800 rounded transition-colors">
      Edit
    </button>
    <button hx-post="/agent" hx-target="#content" hx-vals='{"message":"delete item 123"}'
            class="px-3 py-1.5 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded transition-colors">
      Delete
    </button>
  </div>
</div>
```

### Compact List Item

```html
<div class="flex items-center justify-between py-3 border-b border-slate-800 last:border-0">
  <div class="flex items-center gap-3">
    <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
    <span class="text-white">Item name</span>
  </div>
  <span class="text-sm text-slate-400">metadata</span>
</div>
```

### List Container

```html
<div class="space-y-3">
  <!-- list items here -->
</div>
```

---

## Button Components

### Primary Button

```html
<button hx-post="/agent" hx-target="#content" hx-vals='{"message":"action"}'
        class="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg
               shadow-lg shadow-indigo-500/25 hover:shadow-indigo-500/40
               transition-all duration-200 active:scale-[0.98]">
  Button Text
</button>
```

### Secondary Button

```html
<button hx-post="/agent" hx-target="#content" hx-vals='{"message":"action"}'
        class="px-4 py-2 text-slate-400 hover:text-white hover:bg-slate-800
               rounded-lg transition-all duration-200">
  Button Text
</button>
```

### Ghost Button

```html
<button hx-post="/agent" hx-target="#content" hx-vals='{"message":"action"}'
        class="px-4 py-2 text-indigo-400 hover:text-indigo-300
               transition-colors">
  Button Text
</button>
```

### Danger Button

```html
<button hx-post="/agent" hx-target="#content" hx-vals='{"message":"delete item 123"}'
        class="px-4 py-2 text-red-400 hover:text-red-300 hover:bg-red-500/10
               rounded-lg transition-all duration-200">
  Delete
</button>
```

### Icon Button

```html
<button hx-post="/agent" hx-target="#content" hx-vals='{"message":"action"}'
        class="p-2 text-slate-400 hover:text-white hover:bg-slate-800
               rounded-lg transition-all duration-200">
  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
  </svg>
</button>
```

### Button Group

```html
<div class="flex gap-2">
  <button class="px-4 py-2 bg-indigo-600 text-white rounded-l-lg">Left</button>
  <button class="px-4 py-2 bg-slate-800 text-slate-300">Center</button>
  <button class="px-4 py-2 bg-slate-800 text-slate-300 rounded-r-lg">Right</button>
</div>
```

---

## Form Components

### Text Input

```html
<input type="text" name="field" placeholder="Placeholder..."
       class="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg
              text-white placeholder-slate-500
              focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
              transition-all duration-200">
```

### Textarea

```html
<textarea name="description" rows="4" placeholder="Enter description..."
          class="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg
                 text-white placeholder-slate-500
                 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
                 transition-all duration-200 resize-none"></textarea>
```

### Select

```html
<select name="status"
        class="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg
               text-white focus:outline-none focus:ring-2 focus:ring-indigo-500
               focus:border-transparent transition-all duration-200">
  <option value="active">Active</option>
  <option value="pending">Pending</option>
  <option value="completed">Completed</option>
</select>
```

### Form Field with Label

```html
<div>
  <label class="block text-sm font-medium text-slate-300 mb-2">Field Label</label>
  <input type="text" name="field" required
         class="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white
                placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500
                focus:border-transparent transition-all duration-200">
</div>
```

### Complete Form

```html
<form hx-post="/agent" hx-target="#content" class="space-y-5 animate-in">
  <div>
    <label class="block text-sm font-medium text-slate-300 mb-2">Name</label>
    <input type="text" name="name" required
           class="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white
                  placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500
                  focus:border-transparent transition-all duration-200">
  </div>

  <div>
    <label class="block text-sm font-medium text-slate-300 mb-2">Description</label>
    <textarea name="description" rows="3"
              class="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white
                     placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500
                     focus:border-transparent transition-all duration-200 resize-none"></textarea>
  </div>

  <input type="hidden" name="message" value="create with name and description">

  <div class="flex justify-end gap-3 pt-2">
    <button type="button" hx-post="/agent" hx-target="#content" hx-vals='{"message":"cancel"}'
            class="px-4 py-2.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-all">
      Cancel
    </button>
    <button type="submit"
            class="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg
                   shadow-lg shadow-indigo-500/25 transition-all duration-200">
      Create
    </button>
  </div>
</form>
```

---

## Feedback Components

### Success Alert

```html
<div class="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-lg animate-in">
  <div class="flex items-center gap-3">
    <div class="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center">
      <span class="text-emerald-400">✓</span>
    </div>
    <p class="text-emerald-300 font-medium">Operation completed successfully</p>
  </div>
</div>
```

### Error Alert

```html
<div class="p-4 bg-red-500/10 border border-red-500/30 rounded-lg animate-in">
  <p class="text-red-300">Something went wrong. Please try again.</p>
</div>
```

### Warning Alert

```html
<div class="p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg animate-in">
  <p class="text-amber-300">This action cannot be undone.</p>
</div>
```

### Info Alert

```html
<div class="p-4 bg-indigo-500/10 border border-indigo-500/30 rounded-lg animate-in">
  <p class="text-indigo-300">This is helpful information.</p>
</div>
```

### Empty State

```html
<div class="text-center py-16 animate-in">
  <div class="w-16 h-16 rounded-2xl bg-slate-800 flex items-center justify-center mx-auto mb-4">
    <span class="text-2xl">📋</span>
  </div>
  <h3 class="text-lg font-semibold text-white mb-2">No items yet</h3>
  <p class="text-slate-400 mb-6">Get started by creating your first item</p>
  <button hx-post="/agent" hx-target="#content" hx-vals='{"message":"create new"}'
          class="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg
                 shadow-lg shadow-indigo-500/25 transition-all">
    Create First Item
  </button>
</div>
```

---

## Badge Components

### Default Badge

```html
<span class="px-2.5 py-1 text-xs font-medium rounded-full bg-indigo-500/20 text-indigo-300">
  Label
</span>
```

### Status Badges

```html
<!-- Active/Success -->
<span class="px-2.5 py-1 text-xs font-medium rounded-full bg-emerald-500/20 text-emerald-300">
  Active
</span>

<!-- Warning/Pending -->
<span class="px-2.5 py-1 text-xs font-medium rounded-full bg-amber-500/20 text-amber-300">
  Pending
</span>

<!-- Error/Danger -->
<span class="px-2.5 py-1 text-xs font-medium rounded-full bg-red-500/20 text-red-300">
  Error
</span>

<!-- Neutral/Inactive -->
<span class="px-2.5 py-1 text-xs font-medium rounded-full bg-slate-700 text-slate-400">
  Inactive
</span>
```

---

## Special Components

### Star Rating (Display)

```html
<div class="flex items-center gap-0.5">
  <span class="text-amber-400">★★★★</span>
  <span class="text-slate-600">★</span>
</div>
```

### Star Rating (Input)

```html
<div class="flex items-center gap-1">
  <span class="text-sm text-slate-400 mr-2">Rating:</span>
  <input type="radio" name="rating" value="1" id="star1" class="hidden peer/star1">
  <label for="star1" class="cursor-pointer text-2xl text-slate-600 hover:text-amber-400 peer-checked/star1:text-amber-400">★</label>
  <!-- Repeat for 2-5 -->
</div>
```

### Progress Bar

```html
<div class="w-full bg-slate-800 rounded-full h-2">
  <div class="bg-indigo-600 h-2 rounded-full" style="width: 65%"></div>
</div>
```

### Tabs

```html
<div class="flex gap-1 p-1 bg-slate-800 rounded-lg mb-4">
  <button hx-post="/agent" hx-target="#content" hx-vals='{"message":"show all"}'
          class="flex-1 px-4 py-2 text-sm font-medium rounded-md bg-indigo-600 text-white">
    All
  </button>
  <button hx-post="/agent" hx-target="#content" hx-vals='{"message":"show active"}'
          class="flex-1 px-4 py-2 text-sm font-medium rounded-md text-slate-400 hover:text-white">
    Active
  </button>
  <button hx-post="/agent" hx-target="#content" hx-vals='{"message":"show completed"}'
          class="flex-1 px-4 py-2 text-sm font-medium rounded-md text-slate-400 hover:text-white">
    Completed
  </button>
</div>
```

### Search Bar

```html
<div class="relative mb-6">
  <input type="text" name="query" placeholder="Search..."
         class="w-full pl-10 pr-4 py-3 bg-slate-800 border border-slate-700 rounded-lg
                text-white placeholder-slate-500
                focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent">
  <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
  </svg>
</div>
```

---

## HTMX Reference

### Required Attributes

Every interactive element needs:

```html
hx-post="/agent"           <!-- Send request to agent endpoint -->
hx-target="#content"       <!-- Replace content area -->
hx-vals='{"message":"X"}'  <!-- What action to take -->
```

### Form Pattern

```html
<form hx-post="/agent" hx-target="#content">
  <input type="text" name="field">
  <input type="hidden" name="message" value="action description">
  <button type="submit">Submit</button>
</form>
```

### Loading States (CSS)

```css
.htmx-request #content { opacity: 0.6; pointer-events: none; }
.htmx-request .loading-indicator { display: flex; }
.loading-indicator { display: none; }
```
