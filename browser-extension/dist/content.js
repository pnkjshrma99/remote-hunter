"use strict";
(() => {
  // src/content.ts
  window.__REMOTE_HUNTER_EXTENSION__ = true;
  window.dispatchEvent(new CustomEvent("remotehunterInstalled"));
  function findDeep(selector, root = document) {
    const found = root.querySelector(selector);
    if (found) return found;
    const all = root.querySelectorAll("*");
    for (const el of all) {
      if (el.shadowRoot) {
        const deep = findDeep(selector, el.shadowRoot);
        if (deep) return deep;
      }
    }
    return null;
  }
  function findAllDeep(selector, root = document) {
    const results = [];
    const seen = /* @__PURE__ */ new Set();
    function scan(r) {
      const found = r.querySelectorAll(selector);
      for (const el of found) {
        if (!seen.has(el)) {
          seen.add(el);
          results.push(el);
        }
      }
      const all = r.querySelectorAll("*");
      for (const el of all) {
        if (el.shadowRoot) {
          scan(el.shadowRoot);
        }
      }
    }
    scan(root);
    return results;
  }
  function findFormFields() {
    const fields = [];
    const seen = /* @__PURE__ */ new Set();
    const formElements = findAllDeep(
      "input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=checkbox]):not([type=radio]):not([type=file]), textarea, select, input[type=checkbox], input[type=radio]"
    );
    for (const el of formElements) {
      if (seen.has(el)) continue;
      seen.add(el);
      const inputType = el.type || "text";
      const text = findLabel(el);
      const name = el.getAttribute("name") || el.id || el.getAttribute("data-test-id") || el.getAttribute("data-automation-id") || "";
      fields.push({ el, inputType, text, name });
    }
    return fields;
  }
  function findLabel(el) {
    const id = el.id;
    if (id) {
      const labelEl = findDeep(`label[for="${CSS.escape(id)}"]`);
      if (labelEl) return labelEl.textContent?.trim() || "";
    }
    const root = el.getRootNode();
    if (root instanceof ShadowRoot) {
      const host = root.host;
      const ariaLabel2 = el.getAttribute("aria-label");
      if (ariaLabel2) return ariaLabel2.trim();
      const prev2 = host.previousElementSibling;
      if (prev2) {
        const tag = prev2.tagName.toLowerCase();
        if (["label", "span", "div", "p", "strong"].includes(tag)) {
          const txt = prev2.textContent?.trim();
          if (txt && txt.length < 120) return txt;
        }
      }
      const hostAria = host.getAttribute("aria-label");
      if (hostAria) return hostAria.trim();
      const labelledBy = el.getAttribute("aria-labelledby") || host.getAttribute("aria-labelledby") || "";
      if (labelledBy) {
        const labelEl = document.getElementById(labelledBy);
        if (labelEl) return labelEl.textContent?.trim() || "";
      }
      const innerLabel = root.querySelector("[class*='label'], [class*='heading'], span, label");
      if (innerLabel) {
        const txt = innerLabel.textContent?.trim();
        if (txt && txt.length < 120 && txt.length > 1) return txt;
      }
      return host.getAttribute("name") || host.className || "";
    }
    const parentLabel = el.closest("label");
    if (parentLabel) {
      const text = parentLabel.textContent?.trim() || "";
      return text.replace(el.textContent || "", "").trim() || text;
    }
    const ariaLabel = el.getAttribute("aria-label");
    if (ariaLabel) return ariaLabel.trim();
    const placeholder = el.getAttribute("placeholder");
    if (placeholder) return placeholder.trim();
    const prev = el.previousElementSibling;
    if (prev) {
      const tag = prev.tagName.toLowerCase();
      if (["label", "span", "div", "p", "strong"].includes(tag)) {
        const txt = prev.textContent?.trim();
        if (txt && txt.length < 120) return txt;
      }
    }
    const parent = el.parentElement;
    if (parent) {
      const grandPrev = parent.previousElementSibling;
      if (grandPrev) {
        const txt = grandPrev.textContent?.trim();
        if (txt && txt.length < 120) return txt;
      }
    }
    const describedBy = el.getAttribute("aria-describedby");
    if (describedBy) {
      const descEl = findDeep(`#${CSS.escape(describedBy)}`);
      if (descEl) return descEl.textContent?.trim() || "";
    }
    const name = el.getAttribute("name") || "";
    return name.replace(/[_-]/g, " ").replace(/([a-z])([A-Z])/g, "$1 $2").trim();
  }
  function normalize(text) {
    return text.toLowerCase().replace(/[^a-z0-9]/g, "").trim();
  }
  var FIELD_RULES = [
    { profileKey: "Full Name", keywords: ["fullname", "full name", "full_name", "fullName", "applicantname", "yourname"] },
    { profileKey: "First Name", keywords: ["firstname", "first name", "givenname", "given name", "forename"] },
    { profileKey: "Last Name", keywords: ["lastname", "last name", "surname", "familyname", "family name"] },
    { profileKey: "Middle Name", keywords: ["middlename", "middle name", "middleinitial", "middle initial"] },
    { profileKey: "Email", keywords: ["email", "e-mail", "mail"] },
    { profileKey: "Phone", keywords: ["phone", "telephone", "mobile", "phonenumber", "cell", "contactnumber", "phone number"] },
    { profileKey: "LinkedIn URL", keywords: ["linkedin", "linked in"] },
    { profileKey: "GitHub URL", keywords: ["github", "git hub"] },
    { profileKey: "Portfolio URL", keywords: ["portfolio", "website", "personal site", "personal url", "portfolio url", "url"] },
    { profileKey: "Address", keywords: ["address", "street", "mailing address"] },
    { profileKey: "City", keywords: ["city", "town"] },
    { profileKey: "Country", keywords: ["country", "nation"] },
    { profileKey: "Headline", keywords: ["headline", "title", "professional title", "current title"] },
    { profileKey: "Professional Summary", keywords: ["summary", "professionalsummary", "bio", "about me", "professional summary"] },
    { profileKey: "Company", keywords: ["company", "employer", "organization", "current company", "current employer"] },
    { profileKey: "Title", keywords: ["position", "job title", "job position"] },
    { profileKey: "School", keywords: ["school", "university", "college", "institution", "educational institution"] },
    { profileKey: "Degree", keywords: ["degree", "qualification", "education level", "education"] },
    { profileKey: "Field of Study", keywords: ["field of study", "fieldofstudy", "major", "area of study", "discipline", "subject"] },
    // Visa/authorization rules BEFORE date rules so "visa end date" inputs don't
    // get matched by "End Date" and filled with experience end date values
    { profileKey: "Authorized to work", keywords: ["authorized", "work authorization", "eligible to work", "right to work", "legally authorized", "work permit", "sponsorship"] },
    { profileKey: "Visa Sponsorship", keywords: ["visa", "sponsorship", "h1b", "h-1b", "work visa", "need sponsorship"] },
    { profileKey: "Start Date", keywords: ["startdate", "start date", "from date", "date from"] },
    { profileKey: "End Date", keywords: ["enddate", "end date", "to date", "finish date", "date to", "date end"] },
    { profileKey: "Cover Letter", keywords: ["cover letter", "coverletter", "message", "additional info", "additional information", "why you", "why this company", "introduction"] },
    { profileKey: "Role Description", keywords: ["role description", "roledescription", "job description", "jobdescription", "description", "responsibilities"] },
    { profileKey: "Desired Salary", keywords: ["salary", "desired pay", "compensation", "expected salary", "desired salary", "pay expectation"] },
    { profileKey: "How did you hear", keywords: ["how did you hear", "how did you find", "source", "referral", "found us", "how hear"] },
    { profileKey: "Desired Roles", keywords: ["desired role", "desired position", "position interested", "role interested"] },
    { profileKey: "Remote Only", keywords: ["remote", "work remotely", "remote work", "work from home"] },
    { profileKey: "Open to Relocation", keywords: ["relocation", "willing to relocate", "open to relocate"] },
    { profileKey: "Website", keywords: ["website", "personal website", "homepage"] },
    { profileKey: "GPA", keywords: ["gpa", "grade point average", "grade point"] },
    { profileKey: "Location", keywords: ["location", "where located", "located", "where are you located", "work location", "job location"] },
    { profileKey: "State", keywords: ["state", "province", "region"] },
    { profileKey: "Postal Code", keywords: ["postal", "zip", "zipcode", "postal code", "post code"] },
    { profileKey: "Currently Working", keywords: ["currently working", "currently employed", "current job"] },
    { profileKey: "Notice Period", keywords: ["notice period", "notice"] },
    { profileKey: "Gender", keywords: ["gender", "sex"] },
    { profileKey: "Hispanic/Latino", keywords: ["hispanic", "latino", "latina", "hispanic latino"] },
    { profileKey: "Veteran Status", keywords: ["veteran", "military", "armed forces", "veteran status"] },
    { profileKey: "Disability Status", keywords: ["disability", "disabled", "disability status"] }
  ];
  function findValueForProfileKey(key, sections) {
    const nk = normalize(key);
    for (const section of sections) {
      for (const f of section.fields) {
        const nf = normalize(f.label);
        if (nf.includes(nk) || nk.includes(nf)) return f.value;
      }
    }
    return void 0;
  }
  function setNativeValue(el, value) {
    if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) {
      const proto = el instanceof HTMLInputElement ? window.HTMLInputElement.prototype : window.HTMLTextAreaElement.prototype;
      const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
      if (setter) {
        setter.call(el, value);
      } else {
        el.value = value;
      }
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
      el.dispatchEvent(new Event("blur", { bubbles: true }));
    }
  }
  function fillInput(el, value) {
    setNativeValue(el, value);
    el.style.outline = "2px solid #22c55e";
    el.style.outlineOffset = "1px";
    el.style.borderRadius = "2px";
  }
  function fillCheckbox(el, value) {
    const checked = value.toLowerCase() === "yes" || value === "true";
    const input = el;
    if (input.checked !== checked) {
      input.checked = checked;
      input.dispatchEvent(new Event("change", { bubbles: true }));
      input.dispatchEvent(new Event("input", { bubbles: true }));
    }
    el.style.outline = "2px solid #22c55e";
    el.style.outlineOffset = "1px";
  }
  function fillRadio(group, value) {
    const radios = document.querySelectorAll(
      `input[type="radio"][name="${CSS.escape(group)}"]`
    );
    for (const radio of radios) {
      const label = findLabel(radio).toLowerCase();
      if (label.includes(value.toLowerCase()) || value.toLowerCase().includes(label)) {
        radio.checked = true;
        radio.dispatchEvent(new Event("change", { bubbles: true }));
        radio.style.outline = "2px solid #22c55e";
        radio.style.outlineOffset = "1px";
        break;
      }
    }
  }
  function similarityScore(a, b) {
    const sa = a.toLowerCase().trim();
    const sb = b.toLowerCase().trim();
    if (sa === sb) return 100;
    if (sa.includes(sb) || sb.includes(sa)) return 80;
    const wa = sa.split(/\s+/);
    const wb = sb.split(/\s+/);
    let common = 0;
    for (const wa_i of wa) {
      for (const wb_j of wb) {
        if (wa_i.length > 2 && wb_j.length > 2 && (wa_i.includes(wb_j) || wb_j.includes(wa_i))) common++;
      }
    }
    const max = Math.max(wa.length, wb.length);
    return max > 0 ? common / max * 60 : 0;
  }
  function findBestOption(opts, value) {
    if (!value) return void 0;
    let best;
    let bestScore = -1;
    for (const o of opts) {
      const text = o.text.trim();
      if (!text || text === "Select One" || text === "--" || text === "") continue;
      const score = similarityScore(text, value);
      if (score > bestScore) {
        bestScore = score;
        best = o;
      }
    }
    return bestScore >= 30 ? best : void 0;
  }
  function fillSelect(el, value) {
    const select = el;
    const opts = Array.from(select.options);
    let match = findBestOption(opts, value);
    if (!match) {
      const v = value.toLowerCase();
      if (/b\.?(tech|e|eng|sc|a)/i.test(v) || v.includes("bachelor")) {
        match = findBestOption(opts, "Bachelor");
      }
      if (!match && (/m\.?(tech|e|eng|sc|a)/i.test(v) || v.includes("master"))) {
        match = findBestOption(opts, "Master");
      }
      if (!match && (/ph\.?d/i.test(v) || v.includes("doctor"))) {
        match = findBestOption(opts, "PhD");
      }
      if (!match && (v.includes("high school") || v.includes("diploma") || v.includes("secondary") || v.includes("12th") || v.includes("hsc"))) {
        match = findBestOption(opts, "High School");
      }
      if (!match && /^\d{4}$/.test(v)) {
        match = opts.find((o) => o.text.includes(v) || o.value === v);
      }
    }
    if (!match) {
      const v = value.toLowerCase().trim();
      for (const o of opts) {
        const firstWord = o.text.trim().split(/[\s(,/]+/)[0].toLowerCase();
        if (firstWord === v || v.includes(firstWord) || firstWord.includes(v)) {
          match = o;
          break;
        }
        const parenMatch = o.text.match(/\(([^)]+)\)/);
        if (parenMatch) {
          const parenContent = parenMatch[1].toLowerCase();
          if (parenContent === v || v.includes(parenContent) || parenContent.includes(v)) {
            match = o;
            break;
          }
        }
      }
    }
    if (match) {
      select.value = match.value;
      select.dispatchEvent(new Event("change", { bubbles: true }));
      select.dispatchEvent(new Event("input", { bubbles: true }));
      el.style.outline = "2px solid #22c55e";
    }
  }
  function handleResumeField(sections) {
    const resumeUrl = sections.flatMap((s) => s.fields).find((f) => normalize(f.label).includes("resume") && f.value)?.value;
    if (!resumeUrl) return;
    const fileInput = findDeep(
      'input[type="file"]'
    );
    if (fileInput) {
      fileInput.setAttribute("data-remotehunter-resume", resumeUrl);
      fileInput.style.outline = "3px solid #6366f1";
      fileInput.style.outlineOffset = "2px";
      fileInput.style.borderRadius = "3px";
      const hint = document.createElement("div");
      hint.textContent = "\u{1F4CE} Resume ready \u2014 click to upload";
      hint.style.cssText = "font-size:12px;color:#6366f1;margin-top:4px;font-weight:500;";
      fileInput.parentElement?.appendChild(hint);
    }
  }
  function autoFill(sections) {
    if (isSmartRecruitersPage()) {
      return 0;
    }
    const fields = findFormFields();
    let filledCount = 0;
    const matched = /* @__PURE__ */ new Set();
    for (const field of fields) {
      if (matched.has(field.el)) continue;
      let value;
      for (const rule of FIELD_RULES) {
        const fn = normalize(field.text);
        const nn = normalize(field.name);
        const matchesLabel = rule.keywords.some((k) => fn.includes(normalize(k)));
        const matchesName = rule.keywords.some((k) => nn.includes(normalize(k)));
        if (!matchesLabel && !matchesName) continue;
        value = findValueForProfileKey(rule.profileKey, sections);
        if (value) break;
      }
      if (value === void 0) {
        const fn = normalize(field.text);
        const nn = normalize(field.name);
        const isNameField = (fn.includes("name") || nn.includes("name")) && !fn.includes("first") && !fn.includes("last") && !fn.includes("middle") && !fn.includes("given") && !fn.includes("family") && !fn.includes("surname") && !fn.includes("forename");
        if (isNameField) {
          value = findValueForProfileKey("Full Name", sections);
        }
      }
      if (value === void 0) continue;
      const inputType = field.inputType;
      if (inputType === "checkbox") {
        fillCheckbox(field.el, value);
        filledCount++;
      } else if (inputType === "radio") {
        const name = field.el.getAttribute("name");
        if (name) fillRadio(name, value);
        filledCount++;
      } else if (field.el instanceof HTMLSelectElement) {
        fillSelect(field.el, value);
        filledCount++;
      } else if (field.el instanceof HTMLInputElement || field.el instanceof HTMLTextAreaElement) {
        fillInput(field.el, value);
        filledCount++;
      }
      matched.add(field.el);
    }
    if (sections.length > 0) {
      handleResumeField(sections);
      handleDateFields(sections);
      handleAutocompleteFields(sections);
    }
    return filledCount;
  }
  function parseDateValue(value) {
    const m = value.match(/(\d{1,2})\/(\d{4})/);
    if (m) return { month: m[1], year: m[2] };
    const m2 = value.match(/(\d{4})[-\/](\d{2})/);
    if (m2) return { month: m2[2], year: m2[1] };
    const monthNames = {
      jan: "01",
      feb: "02",
      mar: "03",
      apr: "04",
      may: "05",
      jun: "06",
      jul: "07",
      aug: "08",
      sep: "09",
      oct: "10",
      nov: "11",
      dec: "12"
    };
    const m3 = value.match(/([a-z]{3,})\s*(\d{4})/i);
    if (m3) {
      const mon = m3[1].toLowerCase().slice(0, 3);
      if (monthNames[mon]) return { month: monthNames[mon], year: m3[2] };
    }
    const m4 = value.match(/(20\d{2})/);
    if (m4) return { month: "", year: m4[1] };
    return null;
  }
  function fillDateSelect(select, value, type) {
    const opts = Array.from(select.options);
    let match = opts.find((o) => o.value === value || o.text === value);
    if (!match) {
      if (type === "month") {
        const num = parseInt(value, 10);
        if (!isNaN(num)) {
          match = opts.find((o) => parseInt(o.value, 10) === num || o.text.startsWith(num.toString().padStart(2, "0")));
        }
        if (!match) {
          match = findBestOption(opts, value);
        }
      } else {
        match = opts.find((o) => o.text.includes(value) || o.value.includes(value));
        if (!match) match = findBestOption(opts, value);
      }
    }
    if (match) {
      select.value = match.value;
      select.dispatchEvent(new Event("change", { bubbles: true }));
      select.style.outline = "2px solid #22c55e";
    }
  }
  function handleDateFields(sections) {
    const labels = document.querySelectorAll("label, span, div[role='heading'], legend");
    for (const lbl of labels) {
      const text = lbl.textContent?.trim().toLowerCase() || "";
      const isFrom = text.includes("from") || text.includes("start") || text === "from*" || text.startsWith("from");
      const isTo = text.includes("to") || text.includes("end") || text.includes("finish");
      if (!isFrom && !isTo) continue;
      const parent = lbl.closest("div, fieldset, li, section") || lbl.parentElement;
      if (!parent) continue;
      const monthSelect = parent.querySelector(
        'select[aria-label*="month" i], select[name*="month" i], select[id*="month" i]'
      ) || Array.from(parent.querySelectorAll("select")).find((s) => {
        const opts = Array.from(s.options);
        return opts.length >= 9 && opts.length <= 13 && opts[1]?.value?.match(/^\d{1,2}$/);
      });
      const yearSelect = parent.querySelector(
        'select[aria-label*="year" i], select[name*="year" i], select[id*="year" i]'
      ) || Array.from(parent.querySelectorAll("select")).find((s) => {
        if (s === monthSelect) return false;
        const opts = Array.from(s.options);
        return opts.some((o) => /^(19|20)\d{2}$/.test(o.value) || /^(19|20)\d{2}$/.test(o.text.trim()));
      });
      const monthInput = parent.querySelector('input[name*="month" i], input[placeholder*="month" i], input[aria-label*="month" i]');
      const yearInput = parent.querySelector('input[name*="year" i], input[placeholder*="year" i], input[aria-label*="year" i]');
      if (!monthSelect && !yearSelect && !monthInput && !yearInput) continue;
      let dateValue = "";
      for (const section of sections) {
        for (const f of section.fields) {
          if (isFrom && normalize(f.label).includes("startdate")) {
            dateValue = f.value;
            break;
          }
          if (isTo && normalize(f.label).includes("enddate")) {
            dateValue = f.value;
            break;
          }
        }
      }
      if (!dateValue) continue;
      const parsed = parseDateValue(dateValue);
      if (!parsed) continue;
      if (monthSelect && parsed.month) fillDateSelect(monthSelect, parsed.month, "month");
      if (monthInput && parsed.month) setNativeValue(monthInput, parsed.month);
      if (yearSelect && parsed.year) fillDateSelect(yearSelect, parsed.year, "year");
      if (yearInput && parsed.year) setNativeValue(yearInput, parsed.year);
    }
  }
  function handleAutocompleteFields(sections) {
    const labels = document.querySelectorAll("label, span[role='heading'], legend");
    for (const lbl of labels) {
      const text = lbl.textContent?.trim().toLowerCase() || "";
      const isAuto = text.includes("school") || text.includes("university") || text.includes("institution") || text.includes("degree") || text.includes("field of study") || text.includes("major");
      if (!isAuto) continue;
      const forId = lbl.getAttribute("for");
      let input = null;
      if (forId) input = document.getElementById(forId);
      if (!input) {
        const parent = lbl.closest("div, fieldset, li, section") || lbl.parentElement;
        if (parent) input = parent.querySelector("input:not([type=hidden]):not([type=radio]):not([type=checkbox])");
      }
      if (!input) continue;
      let profileValue = "";
      const textNorm = normalize(text);
      for (const section of sections) {
        for (const f of section.fields) {
          const fn = normalize(f.label);
          if (!f.value) continue;
          if ((textNorm.includes("school") || textNorm.includes("institution") || textNorm.includes("university")) && (fn.includes("school") || fn.includes("institution") || fn.includes("university"))) {
            profileValue = f.value;
            break;
          }
          if ((textNorm.includes("degree") || textNorm.includes("qualification")) && (fn.includes("degree") || fn.includes("qualification") || fn.includes("education"))) {
            profileValue = f.value;
            break;
          }
          if ((textNorm.includes("fieldofstudy") || textNorm.includes("major") || textNorm.includes("discipline")) && (fn.includes("fieldofstudy") || fn.includes("major") || fn.includes("discipline") || fn.includes("subject"))) {
            profileValue = f.value;
            break;
          }
        }
      }
      if (!profileValue) continue;
      input.value = "";
      let idx = 0;
      const typeInterval = setInterval(() => {
        if (idx < profileValue.length) {
          input.value += profileValue[idx];
          input.dispatchEvent(new Event("input", { bubbles: true }));
          input.dispatchEvent(new Event("keydown", { bubbles: true }));
          input.dispatchEvent(new Event("keyup", { bubbles: true }));
          idx++;
        } else {
          clearInterval(typeInterval);
        }
      }, 60);
      input.style.outline = "2px solid #22c55e";
      setTimeout(() => checkAutocompleteResults(input, profileValue), profileValue.length * 60 + 1e3);
    }
  }
  function checkAutocompleteResults(input, value) {
    const parent = input.closest("div[class*='autocomplete'], div[class*='typeahead'], div[class*='search'], div[role='combobox'], div[class*='dropdown'], li, fieldset, section") || input.parentElement;
    if (!parent) return;
    setTimeout(() => {
      const allItems = parent.querySelectorAll(
        'li, [role="option"], [role="listbox"] li, [class*="option"], [class*="result"], [class*="suggestion"], [class*="menu-item"]'
      );
      const visibleItems = [];
      for (const item of allItems) {
        const rect = item.getBoundingClientRect();
        const style = window.getComputedStyle(item);
        if (style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0) {
          visibleItems.push(item);
        }
      }
      if (visibleItems.length > 0) {
        const hasResults = visibleItems.some((item) => {
          const txt = item.textContent?.trim().toLowerCase() || "";
          return txt.length > 1 && !txt.includes("no result") && !txt.includes("0 item") && !txt.includes("no match");
        });
        if (hasResults) {
          const sv = value.toLowerCase();
          let bestItem = visibleItems[0];
          let bestScore = 0;
          for (const item of visibleItems) {
            const txt = item.textContent?.trim().toLowerCase() || "";
            const score = similarityScore(txt, sv);
            if (score > bestScore) {
              bestScore = score;
              bestItem = item;
            }
          }
          bestItem.click();
          return;
        }
      }
      const otherSelectors = [
        // Workday-specific: "My school is not listed", "I don't see my school"
        'a:not([href="#"])',
        "button",
        "span[tabindex]",
        '[role="button"]',
        'div[class*="link"]'
      ];
      const scope = parent.closest("form, div[role='main'], body") || document.body;
      const clickables = scope.querySelectorAll(otherSelectors.join(","));
      for (const el of clickables) {
        const txt = el.textContent?.trim().toLowerCase() || "";
        if (txt.length > 50 || txt.length < 3) continue;
        if (txt.includes("other") || txt.includes("not listed") || txt.includes("can't find") || txt.includes("add manually") || txt.includes("school not listed") || txt.includes("don't see") || txt.includes("not in list") || txt.includes("my school") || txt.includes("my institution") || txt.includes("type your own") || txt.includes("enter manually")) {
          el.click();
          return;
        }
      }
    }, 600);
  }
  function getSRContext() {
    return window.__OC_CONTEXT__;
  }
  function isSmartRecruitersPage() {
    return !!getSRContext()?.screeningConfiguration?.questions;
  }
  function getSRQuestions() {
    return getSRContext()?.screeningConfiguration?.questions || [];
  }
  function waitForNativeSelects(maxWaitMs = 8e3) {
    return new Promise((resolve) => {
      const check = () => {
        const selects = findAllDeep("select");
        const questions = getSRQuestions().filter((q) => q.type !== "info");
        if (selects.length >= questions.length) {
          resolve(true);
          return;
        }
        if (selects.length > 0 && selects.length >= Math.ceil(questions.length / 2)) {
          resolve(true);
          return;
        }
        setTimeout(check, 300);
      };
      check();
      setTimeout(() => resolve(false), maxWaitMs);
    });
  }
  function srNormalize(text) {
    return text.toLowerCase().replace(/[^a-z0-9\/\s]/g, "").trim();
  }
  function srOptionsMatch(selectOpts, questionOpts) {
    if (selectOpts.length <= 1 || questionOpts.length === 0) return false;
    const startIdx = selectOpts[0]?.value === "" || selectOpts[0]?.text.trim() === "" ? 1 : 0;
    const selectLabels = selectOpts.slice(startIdx).map((o) => srNormalize(o.text));
    const questionLabels = questionOpts.map((o) => srNormalize(o));
    let matchCount = 0;
    for (const sl of selectLabels) {
      if (sl.length < 2) continue;
      if (questionLabels.some((ql) => ql.includes(sl) || sl.includes(ql))) {
        matchCount++;
      }
    }
    const minMatch = Math.min(selectLabels.length, questionLabels.length);
    return minMatch > 0 && matchCount >= Math.max(2, Math.ceil(minMatch * 0.4));
  }
  function findQuestionForSelect(select, questions) {
    const opts = Array.from(select.options);
    if (opts.length <= 1) return null;
    for (const q of questions) {
      if (q.type === "info") continue;
      const field = q.questionsFields?.[0];
      if (!field?.questionsFieldValues?.length) continue;
      const qOpts = field.questionsFieldValues.map((v) => v.label);
      if (srOptionsMatch(opts, qOpts)) {
        return q;
      }
    }
    return null;
  }
  function srFindOptionByText(select, value) {
    const opts = Array.from(select.options);
    if (opts.length <= 1) return null;
    const startIdx = opts[0]?.value === "" || opts[0]?.text.trim() === "" ? 1 : 0;
    const relevantOpts = opts.slice(startIdx);
    const vLower = value.toLowerCase().trim();
    const exact = relevantOpts.find(
      (o) => o.text.trim().toLowerCase() === vLower || o.value.toLowerCase() === vLower
    );
    if (exact) return exact;
    const contains = relevantOpts.find(
      (o) => o.text.toLowerCase().includes(vLower) || o.value.toLowerCase().includes(vLower)
    );
    if (contains) return contains;
    return findBestOption(relevantOpts, value) || null;
  }
  function srMapQuestionToProfileValue(question, sections) {
    const label = question.label;
    const ql = srNormalize(label);
    const profileMap = [
      [/(hear|find|source|referral)/, "How did you hear"],
      [/(sex|gender)/, "Gender"],
      [/(veteran|military)/, "Veteran Status"],
      [/(disability)/, "Disability Status"],
      [/(hispanic|latino)/, "Hispanic/Latino"],
      [/(motivat)/, "Cover Letter"],
      [/(school|university|college|institut)/, "School"],
      [/(degree|qualification|education)/, "Degree"],
      [/(major|field of study)/, "Field of Study"],
      [/(location)/, "Location"],
      [/(city)/, "City"],
      [/(country)/, "Country"],
      [/(phone|telephone|mobile)/, "Phone"],
      [/(email|e-mail)/, "Email"],
      [/(name|full name)/, "Full Name"],
      [/(linkedin)/, "LinkedIn URL"],
      [/(github)/, "GitHub URL"],
      [/(portfolio|website|url)/, "Portfolio URL"],
      [/(salary|pay|compensation)/, "Desired Salary"],
      [/(role|position)/, "Desired Roles"],
      [/(remote)/, "Remote Only"],
      [/(relocat)/, "Open to Relocation"],
      [/(work auth|sponsor|visa|eligible|right to work)/, "Authorized to work"],
      [/(notice)/, "Notice Period"],
      [/(ever worked|work at|employ)/, "Company"]
    ];
    for (const [pattern, profileKey] of profileMap) {
      if (pattern.test(ql)) {
        const val = findValueForProfileKey(profileKey, sections);
        if (val) return val;
      }
    }
    return void 0;
  }
  async function handleSmartRecruiters(sections) {
    if (!isSmartRecruitersPage()) return 0;
    const questions = getSRQuestions().filter((q) => q.type !== "info");
    if (!questions.length) return 0;
    const found = await waitForNativeSelects();
    const allSelects = findAllDeep("select");
    let filledCount = 0;
    const filledLabels = /* @__PURE__ */ new Set();
    for (const select of allSelects) {
      const question = findQuestionForSelect(select, questions);
      if (!question || filledLabels.has(question.label)) continue;
      filledLabels.add(question.label);
      const profileValue = srMapQuestionToProfileValue(question, sections);
      if (!profileValue) continue;
      const field = question.questionsFields?.[0];
      const isMulti = field?.multipleChoice === true;
      if (isMulti) {
        const container = select.closest("div, fieldset, li, section") || select.parentElement;
        if (container) {
          const checkboxes = container.querySelectorAll(
            'input[type="checkbox"], [role="checkbox"]'
          );
          let multiFilled = false;
          for (const cb of checkboxes) {
            const cbLabel = cb.nextSibling?.textContent?.trim().toLowerCase() || "";
            if (!cbLabel) continue;
            if (cbLabel.includes(profileValue.toLowerCase()) || profileValue.toLowerCase().includes(cbLabel)) {
              if (cb instanceof HTMLInputElement) {
                cb.checked = true;
                cb.dispatchEvent(new Event("change", { bubbles: true }));
                cb.dispatchEvent(new Event("input", { bubbles: true }));
              } else {
                cb.click();
              }
              multiFilled = true;
              break;
            }
          }
          if (!multiFilled) {
            const opt = srFindOptionByText(select, profileValue);
            if (opt) {
              select.value = opt.value;
              select.dispatchEvent(new Event("change", { bubbles: true }));
              select.dispatchEvent(new Event("input", { bubbles: true }));
              multiFilled = true;
            }
          }
          if (multiFilled) {
            container.querySelector("select, button, div[class*='select']")?.style?.setProperty("outline", "2px solid #22c55e", "important");
            filledCount++;
          }
        }
      } else {
        const opt = srFindOptionByText(select, profileValue);
        if (opt) {
          select.value = opt.value;
          select.dispatchEvent(new Event("change", { bubbles: true }));
          select.dispatchEvent(new Event("input", { bubbles: true }));
          select.style.outline = "2px solid #22c55e";
          filledCount++;
        }
      }
    }
    return filledCount;
  }
  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message.type === "AUTOFILL") {
      chrome.storage.local.get("remote_hunter_profile").then(async (result) => {
        const profile = result.remote_hunter_profile;
        if (!profile || !profile.sections.length) {
          sendResponse({
            success: false,
            error: "No profile data. Open the extension popup and connect first.",
            filled: 0
          });
          return;
        }
        if (isSmartRecruitersPage()) {
          const filled2 = await handleSmartRecruiters(profile.sections);
          sendResponse({
            success: filled2 > 0,
            filled: filled2,
            message: filled2 > 0 ? `\u2713 Auto-filled ${filled2} SmartRecruiters field(s)` : "Could not fill SmartRecruiters fields. Try clicking dropdowns manually."
          });
          return;
        }
        const filled = autoFill(profile.sections);
        sendResponse({
          success: filled > 0,
          filled,
          message: filled > 0 ? `\u2713 Auto-filled ${filled} field(s)` : "No matching form fields found on this page."
        });
      });
      return true;
    }
    if (message.type === "SCRAPE_FIELDS") {
      const fields = findFormFields().map((f) => ({
        label: f.text,
        name: f.name,
        type: f.inputType
      }));
      sendResponse({ fields });
      return true;
    }
    if (message.type === "SMART_FILL") {
      const { fields } = message;
      let filled = 0;
      for (const f of fields) {
        const name = f.name;
        const label = f.label;
        let el = null;
        if (name) {
          el = document.querySelector(`[name="${CSS.escape(name)}"], #${CSS.escape(name)}`);
        }
        if (!el && label) {
          const labels = document.querySelectorAll("label");
          for (const lbl of labels) {
            if (lbl.textContent?.trim().toLowerCase().includes(label.toLowerCase())) {
              const forId = lbl.getAttribute("for");
              if (forId) {
                el = document.getElementById(forId);
                if (el) break;
              }
            }
          }
        }
        if (!el) {
          if (label) {
            el = document.querySelector(`[placeholder="${CSS.escape(label)}"]`);
          }
        }
        if (!el) continue;
        if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) {
          setNativeValue(el, f.value);
          el.style.outline = "2px solid #22c55e";
          el.style.outlineOffset = "1px";
          filled++;
        } else if (el instanceof HTMLSelectElement) {
          const opts = Array.from(el.options);
          const match = opts.find((o) => o.text.toLowerCase().includes(f.value.toLowerCase()));
          if (match) {
            el.value = match.value;
            el.dispatchEvent(new Event("change", { bubbles: true }));
            el.style.outline = "2px solid #22c55e";
            el.style.outlineOffset = "1px";
            filled++;
          }
        }
      }
      sendResponse({ success: filled > 0, filled });
      return true;
    }
  });
  window.addEventListener("message", (event) => {
    if (event.data?.type === "RH_AUTOFILL" && event.data?.jobUrl) {
      chrome.storage.local.get("remote_hunter_profile").then(async (result) => {
        const profile = result.remote_hunter_profile;
        if (!profile?.sections.length) return;
        if (isSmartRecruitersPage()) {
          await handleSmartRecruiters(profile.sections);
        } else {
          autoFill(profile.sections);
        }
      });
    }
  });
  (async () => {
    const result = await chrome.storage.local.get("remote_hunter_profile");
    if (result.remote_hunter_profile) {
      const profile = result.remote_hunter_profile;
      if (isSmartRecruitersPage()) {
        await handleSmartRecruiters(profile.sections);
      } else {
        const filled = autoFill(profile.sections);
        if (filled > 0) {
          console.log(`[Remote Hunter] Auto-filled ${filled} field(s).`);
        }
      }
    }
  })();
})();
