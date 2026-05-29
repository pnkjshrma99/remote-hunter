export interface AutofillField {
  label: string;
  value: string;
  field_type: string;
}

export interface AutofillSection {
  title: string;
  fields: AutofillField[];
}

export interface ProfileData {
  sections: AutofillSection[];
  resume_url?: string;
  resume_name?: string;
}

export interface StoredAuth {
  api_url: string;
  token: string;
  email: string;
}

export interface FieldMapping {
  label: string;
  value: string;
  fieldType: string;
}
