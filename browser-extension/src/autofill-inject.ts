/* Standalone autofill injected via chrome.scripting.executeScript as fallback. */

type InjectField = { el: HTMLElement; inputType: string; text: string; name: string };

function findLabel(el: HTMLElement): string {
  const id = el.id;
  if (id) {
    const labelEl = document.querySelector(`label[for="${CSS.escape(id)}"]`);
    if (labelEl) return labelEl.textContent?.trim() || "";
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
  if (prev && ["label", "span", "div", "p", "strong"].includes(prev.tagName.toLowerCase())) {
    const txt = prev.textContent?.trim();
    if (txt && txt.length < 120) return txt;
  }
  const parent = el.parentElement;
  if (parent) {
    const grandPrev = parent.previousElementSibling;
    if (grandPrev) {
      const txt = grandPrev.textContent?.trim();
      if (txt && txt.length < 120) return txt;
    }
  }
  return el.getAttribute("name") || "";
}

function getFields(): InjectField[] {
  const fields: InjectField[] = [];
  const seen = new Set<HTMLElement>();
  const els = document.querySelectorAll<HTMLElement>(
    "input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=file]), textarea, select, input[type=checkbox], input[type=radio]"
  );
  for (const el of els) {
    if (seen.has(el)) continue;
    seen.add(el);
    fields.push({
      el,
      inputType: (el as HTMLInputElement).type || "text",
      text: findLabel(el),
      name: el.getAttribute("name") || el.id || el.getAttribute("data-test-id") || "",
    });
  }
  return fields;
}

function norm(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]/g, "").trim();
}

const FIELD_RULES: { pk: string; kw: string[] }[] = [
  { pk: "Full Name", kw: ["fullname", "full name", "applicantname", "yourname"] },
  { pk: "First Name", kw: ["firstname", "first name", "givenname", "given name", "forename"] },
  { pk: "Last Name", kw: ["lastname", "last name", "surname", "familyname", "family name"] },
  { pk: "Middle Name", kw: ["middlename", "middle name", "middleinitial", "middle initial"] },
  { pk: "Email", kw: ["email", "e-mail", "mail"] },
  { pk: "Phone", kw: ["phone", "telephone", "mobile", "phonenumber", "cell", "phone number"] },
  { pk: "LinkedIn URL", kw: ["linkedin", "linked in"] },
  { pk: "GitHub URL", kw: ["github", "git hub"] },
  { pk: "Portfolio URL", kw: ["portfolio", "website", "personal site", "portfolio url", "url"] },
  { pk: "Address", kw: ["address", "street"] },
  { pk: "City", kw: ["city", "town"] },
  { pk: "Country", kw: ["country", "nation"] },
  { pk: "Headline", kw: ["headline", "title", "professional title"] },
  { pk: "Professional Summary", kw: ["summary", "bio", "about me", "professional summary"] },
  { pk: "Company", kw: ["company", "employer", "organization", "current company"] },
  { pk: "Title", kw: ["position", "job title", "job position"] },
  { pk: "School", kw: ["school", "university", "college", "institution", "educational institution"] },
  { pk: "Degree", kw: ["degree", "qualification", "education level", "education"] },
  { pk: "Field of Study", kw: ["field of study", "fieldofstudy", "major", "area of study", "discipline", "subject"] },
  { pk: "Start Date", kw: ["start date", "startdate", "from", "start"] },
  { pk: "End Date", kw: ["end date", "enddate", "to", "end", "finish"] },
  { pk: "Cover Letter", kw: ["cover letter", "coverletter", "message", "additional info", "why you", "why this company", "introduction"] },
  { pk: "Role Description", kw: ["role description", "roledescription", "job description", "jobdescription", "description", "responsibilities"] },
  { pk: "Desired Salary", kw: ["salary", "desired pay", "compensation", "expected salary", "desired salary"] },
  { pk: "How did you hear", kw: ["how did you hear", "source", "referral", "found us"] },
  { pk: "Desired Roles", kw: ["desired role", "desired position"] },
  { pk: "Remote Only", kw: ["remote", "work remotely", "remote work"] },
  { pk: "Open to Relocation", kw: ["relocation", "willing to relocate"] },
  { pk: "GPA", kw: ["gpa", "grade point average"] },
  { pk: "Location", kw: ["location", "work location", "where located", "located", "where are you located"] },
  { pk: "State", kw: ["state", "province", "region"] },
  { pk: "Postal Code", kw: ["postal", "zip", "zipcode", "postal code", "post code"] },
  { pk: "Authorized to work", kw: ["authorized", "work authorization", "eligible to work", "right to work"] },
  { pk: "Visa Sponsorship", kw: ["visa", "sponsorship", "h1b", "h-1b", "work visa"] },
  { pk: "Gender", kw: ["gender", "sex"] },
  { pk: "Hispanic/Latino", kw: ["hispanic", "latino", "hispanic latino"] },
  { pk: "Veteran Status", kw: ["veteran", "military", "veteran status"] },
  { pk: "Disability Status", kw: ["disability", "disabled", "disability status"] },
];

function findValue(pk: string, sections: any[]): string | undefined {
  const npk = norm(pk);
  for (const s of sections) {
    for (const f of s.fields) {
      if (norm(f.label).includes(npk) || npk.includes(norm(f.label))) return f.value;
    }
  }
  return undefined;
}

(async () => {
  const storage = await chrome.storage.local.get("remote_hunter_profile");
  const profile = storage.remote_hunter_profile as { sections: any[]; resume_url?: string; resume_name?: string } | undefined;
  if (!profile?.sections?.length) {
    return { success: false, error: "No profile data found. Open the extension popup and connect first.", filled: 0 };
  }

  const fields = getFields();
  let filledCount = 0;
  const matched = new Set<HTMLElement>();

  for (const field of fields) {
    if (matched.has(field.el)) continue;
    const fn = norm(field.text);
    const nn = norm(field.name);
    let value: string | undefined;
    for (const rule of FIELD_RULES) {
      if (!rule.kw.some((k) => fn.includes(norm(k)) || nn.includes(norm(k)))) continue;
      value = findValue(rule.pk, profile.sections);
      if (value) break;
    }
    if (value === undefined) continue;

    const type = field.inputType;
    if (type === "checkbox") {
      const checked = value.toLowerCase() === "yes" || value === "true";
      (field.el as HTMLInputElement).checked = checked;
      field.el.dispatchEvent(new Event("change", { bubbles: true }));
      field.el.style.outline = "2px solid #22c55e";
      filledCount++;
    } else if (type === "radio") {
      const name = field.el.getAttribute("name");
      if (name) {
        document.querySelectorAll<HTMLInputElement>(`input[type="radio"][name="${CSS.escape(name)}"]`).forEach((r) => {
          if (findLabel(r).toLowerCase().includes(value!.toLowerCase())) {
            r.checked = true;
            r.dispatchEvent(new Event("change", { bubbles: true }));
            r.style.outline = "2px solid #22c55e";
          }
        });
      }
      filledCount++;
    } else if (field.el instanceof HTMLSelectElement) {
      const match = Array.from(field.el.options).find(
        (o) => o.text.toLowerCase().includes(value.toLowerCase()) || value.toLowerCase().includes(o.text.toLowerCase())
      );
      if (match) {
        field.el.value = match.value;
        field.el.dispatchEvent(new Event("change", { bubbles: true }));
        field.el.style.outline = "2px solid #22c55e";
      }
      filledCount++;
    } else {
      const setter = Object.getOwnPropertyDescriptor(
        field.el instanceof HTMLInputElement ? HTMLInputElement.prototype : HTMLTextAreaElement.prototype,
        "value"
      )?.set;
      if (setter) setter.call(field.el, value);
      else (field.el as HTMLInputElement).value = value;
      field.el.dispatchEvent(new Event("input", { bubbles: true }));
      field.el.dispatchEvent(new Event("change", { bubbles: true }));
      field.el.dispatchEvent(new Event("blur", { bubbles: true }));
      field.el.style.outline = "2px solid #22c55e";
      filledCount++;
    }
    matched.add(field.el);
  }

  if (profile.resume_url) {
    const fileInput = document.querySelector<HTMLInputElement>('input[type="file"]');
    if (fileInput) {
      fileInput.setAttribute("data-remotehunter-resume", profile.resume_url);
      fileInput.style.outline = "3px solid #6366f1";
    }
  }

  return {
    success: filledCount > 0,
    filled: filledCount,
    message: filledCount > 0 ? `✓ Auto-filled ${filledCount} field(s)` : "No matching form fields found.",
  };
})();
