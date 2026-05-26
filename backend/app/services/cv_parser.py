"""CV parsing service to extract skills, experience, and tech stack from resumes."""

import re
from typing import Dict, List, Optional
from datetime import datetime


class CVParser:
    """Parse CV text to extract structured information."""
    
    # Comprehensive tech stack keywords
    TECH_KEYWORDS = {
        'languages': [
            'python', 'javascript', 'typescript', 'java', 'c++', 'c#', 'go', 'golang', 'rust', 'php', 'ruby', 
            'swift', 'kotlin', 'scala', 'r', 'sql', 'html', 'css', 'bash', 'shell', 'powershell', 'perl',
            'lua', 'dart', 'matlab', 'julia', 'haskell', 'elixir', 'f#', 'clojure', 'groovy', 'objective-c'
        ],
        'frameworks': [
            'react', 'vue', 'angular', 'django', 'flask', 'fastapi', 'spring', 'spring boot', 'express', 
            'next.js', 'nuxt.js', 'rails', 'laravel', 'svelte', 'ember', 'backbone', 'jquery', 'bootstrap',
            'tailwind', 'material ui', 'ant design', 'chakra ui', 'redux', 'mobx', 'vuex', 'ngrx',
            'nestjs', 'koa', 'hapi', 'sinatra', 'falcon', 'tornado', 'aiohttp', 'quart'
        ],
        'databases': [
            'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch', 'sqlite', 'oracle', 'cassandra', 
            'dynamodb', 'mariadb', 'cockroachdb', 'neo4j', 'influxdb', 'timescaledb', 'firestore',
            'supabase', 'fauna', 'prisma', 'sequelize', 'typeorm', 'sqlalchemy', 'hibernate', 'mongoose'
        ],
        'cloud': [
            'aws', 'azure', 'gcp', 'google cloud', 'digitalocean', 'linode', 'heroku', 'vercel', 'netlify',
            'docker', 'kubernetes', 'k8s', 'terraform', 'ansible', 'chef', 'puppet', 'saltstack',
            'jenkins', 'gitlab ci', 'github actions', 'circleci', 'travis ci', 'bamboo', 'teamcity'
        ],
        'tools': [
            'git', 'github', 'gitlab', 'bitbucket', 'svn', 'mercurial', 'linux', 'ubuntu', 'debian', 'centos',
            'jira', 'confluence', 'slack', 'discord', 'figma', 'sketch', 'adobe xd', 'trello', 'asana',
            'notion', 'obsidian', 'vs code', 'intellij', 'pycharm', 'webstorm', 'vim', 'emacs'
        ],
        'devops': [
            'ci/cd', 'continuous integration', 'continuous deployment', 'devops', 'sre', 'site reliability',
            'monitoring', 'logging', 'alerting', 'prometheus', 'grafana', 'elk', 'elasticsearch', 'logstash', 'kibana',
            'splunk', 'datadog', 'new relic', 'pagerduty', 'nagios', 'zabbix'
        ],
        'ml': [
            'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy', 'keras', 'nlp', 'natural language processing',
            'machine learning', 'deep learning', 'ai', 'artificial intelligence', 'computer vision',
            'opencv', 'hugging face', 'transformers', 'langchain', 'openai', 'gpt', 'llm', 'large language models'
        ],
        'testing': [
            'jest', 'mocha', 'jasmine', 'karma', 'pytest', 'unittest', 'selenium', 'cypress', 'playwright',
            'testing library', 'supertest', 'chai', 'sinon', 'junit', 'testng', 'rspec', 'cucumber'
        ],
        'mobile': [
            'react native', 'flutter', 'ionic', 'android', 'ios', 'swiftui', 'jetpack compose', 'xamarin',
            'cordova', 'phonegap', 'native', 'kotlin', 'swift', 'objective-c'
        ],
        'data': [
            'spark', 'hadoop', 'kafka', 'airflow', 'dbt', 'looker', 'tableau', 'power bi', 'metabase',
            'grafana', 'superset', 'redshift', 'snowflake', 'bigquery', 'databricks', 'etl', 'data engineering'
        ]
    }
    
    # Job role keywords
    JOB_ROLES = [
        'software engineer', 'full stack developer', 'frontend developer', 'backend developer',
        'devops engineer', 'site reliability engineer', 'sre', 'cloud engineer',
        'data engineer', 'data scientist', 'machine learning engineer', 'ml engineer',
        'mobile developer', 'android developer', 'ios developer',
        'web developer', 'web application developer', 'full stack web developer',
        'backend developer', 'server-side developer', 'api developer',
        'frontend developer', 'ui developer', 'ux developer',
        'software architect', 'technical architect', 'solutions architect',
        'platform engineer', 'infrastructure engineer',
        'security engineer', 'cybersecurity engineer',
        'qa engineer', 'quality assurance engineer', 'test engineer',
        'product manager', 'technical product manager',
        'engineering manager', 'tech lead', 'team lead',
        'senior engineer', 'staff engineer', 'principal engineer',
        'junior engineer', 'entry-level engineer'
    ]
    
    # Common skills keywords
    SKILL_KEYWORDS = [
        'agile', 'scrum', 'kanban', 'leadership', 'communication', 'problem solving',
        'team management', 'project management', 'data analysis', 'software development',
        'web development', 'mobile development', 'backend', 'frontend', 'full stack',
        'system design', 'architecture', 'api design', 'microservices', 'rest api',
        'graphql', 'testing', 'unit testing', 'integration testing', 'tdd', 'code review',
        'debugging', 'optimization', 'performance tuning', 'security', 'cryptography',
        'monitoring', 'logging', 'documentation', 'mentoring', 'training',
        'collaboration', 'cross-functional', 'stakeholder management', 'agile methodologies',
        'continuous integration', 'continuous deployment', 'devops practices',
        'cloud computing', 'distributed systems', 'scalability', 'availability',
        'database design', 'data modeling', 'api development', 'web services',
        'version control', 'git workflow', 'code quality', 'best practices',
        'troubleshooting', 'root cause analysis', 'incident response',
        'automation', 'scripting', 'infrastructure as code',
        'containerization', 'orchestration', 'service mesh',
        'observability', 'metrics', 'tracing', 'alerting'
    ]
    
    @staticmethod
    def extract_tech_stack(text: str) -> List[str]:
        """Extract tech stack keywords from CV text."""
        text_lower = text.lower()
        found_tech = set()
        
        for category, keywords in CVParser.TECH_KEYWORDS.items():
            for keyword in keywords:
                # Use word boundaries for better matching
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, text_lower, re.IGNORECASE):
                    found_tech.add(keyword)
        
        return sorted(list(found_tech))
    
    @staticmethod
    def extract_skills(text: str) -> List[str]:
        """Extract general skills from CV text."""
        text_lower = text.lower()
        found_skills = set()
        
        for skill in CVParser.SKILL_KEYWORDS:
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, text_lower, re.IGNORECASE):
                found_skills.add(skill)
        
        return sorted(list(found_skills))
    
    @staticmethod
    def extract_job_roles(text: str) -> List[str]:
        """Extract job roles/titles from CV text."""
        text_lower = text.lower()
        found_roles = set()
        
        for role in CVParser.JOB_ROLES:
            pattern = r'\b' + re.escape(role) + r'\b'
            if re.search(pattern, text_lower, re.IGNORECASE):
                found_roles.add(role)
        
        return sorted(list(found_roles))
    
    @staticmethod
    def extract_experience_years(text: str) -> Optional[int]:
        """Extract total years of experience from CV text."""
        # Look for patterns like "5 years experience", "5+ years", "5 years of"
        patterns = [
            r'(\d+)\+?\s*years?\s*(of\s*)?(experience|work|professional\s*experience)',
            r'(\d+)\s*years?\s*(of\s*)?(total\s*)?experience',
            r'experience\s*:\s*(\d+)\+?\s*years?',
            r'total\s*experience\s*:\s*(\d+)\+?\s*years?',
            r'(\d+)\s*years?\s*of\s*professional\s*experience',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text.lower())
            if matches:
                try:
                    return int(matches[0][0] if isinstance(matches[0], tuple) else matches[0])
                except (ValueError, IndexError):
                    continue
        
        return None
    
    @staticmethod
    def extract_education(text: str) -> List[Dict]:
        """Extract education information from CV text."""
        education = []
        
        # Common degree patterns
        degree_patterns = [
            r'(bachelor|master|phd|doctorate|b\.s\.|m\.s\.|b\.a\.|m\.a\.|b\.tech|m\.tech|b\.e|m\.e)',
            r'(computer science|software engineering|information technology|data science|computer engineering)',
            r'(mba|mca|bca|b\.com|m\.com)',
        ]
        
        # Look for education sections
        lines = text.split('\n')
        in_education = False
        current_edu = {}
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Detect education section
            if any(keyword in line_lower for keyword in ['education', 'academic', 'university', 'college', 'qualification']):
                in_education = True
                continue
            
            # Exit education section if we hit another major section
            if in_education and any(keyword in line_lower for keyword in ['experience', 'work', 'skills', 'projects']):
                if current_edu:
                    education.append(current_edu)
                    current_edu = {}
                in_education = False
                continue
            
            if in_education:
                # Extract degree
                for pattern in degree_patterns:
                    match = re.search(pattern, line_lower, re.IGNORECASE)
                    if match:
                        current_edu['degree'] = match.group()
                        break
                
                # Extract year
                year_match = re.search(r'(19|20)\d{2}', line)
                if year_match:
                    current_edu['year'] = year_match.group()
                
                # Extract university/institution name
                if 'university' in line_lower or 'institute' in line_lower or 'college' in line_lower:
                    current_edu['institution'] = line.strip()
                
                # If we have degree and year, add to education list
                if 'degree' in current_edu and 'year' in current_edu:
                    education.append(current_edu)
                    current_edu = {}
        
        return education
    
    @staticmethod
    def extract_certifications(text: str) -> List[str]:
        """Extract certifications from CV text."""
        certifications = []
        
        # Common certification keywords
        cert_keywords = [
            'aws certified', 'aws solutions architect', 'aws developer', 'aws sysops',
            'azure certified', 'azure administrator', 'azure developer',
            'gcp certified', 'google cloud certified',
            'pmp', 'project management professional',
            'scrum master', 'csm', 'cspo', 'agile certified',
            'ccna', 'ccnp', 'ccie', 'cisco',
            'cissp', 'ceh', 'security+',
            'google cloud professional', 'microsoft certified',
            'oracle certified', 'salesforce certified',
            'kubernetes certified', 'cka', 'ckad',
            'docker certified', 'red hat certified',
            'tableau certified', 'power bi certified'
        ]
        
        text_lower = text.lower()
        for cert in cert_keywords:
            pattern = r'\b' + re.escape(cert) + r'\b'
            if re.search(pattern, text_lower, re.IGNORECASE):
                certifications.append(cert)
        
        return sorted(list(set(certifications)))
    
    @staticmethod
    def extract_keywords(text: str) -> List[str]:
        """Extract important keywords from CV text using frequency analysis."""
        # Remove common words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be', 'been', 'being', 'have', 'has',
            'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
            'must', 'shall', 'can', 'need', 'dare', 'ought', 'used', 'i', 'you', 'he', 'she',
            'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'its',
            'our', 'their', 'this', 'that', 'these', 'those', 'am', 'is', 'are', 'was', 'were',
            'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'but', 'and',
            'if', 'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with',
            'about', 'against', 'between', 'into', 'through', 'during', 'before', 'after',
            'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over',
            'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where',
            'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other',
            'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too',
            'very', 's', 't', 'can', 'will', 'just', 'don', 'should', 'now'
        }
        
        # Tokenize and count word frequency
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        word_freq = {}
        
        for word in words:
            if word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get top keywords by frequency
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        top_keywords = [word for word, freq in sorted_words[:30] if freq >= 2]
        
        return sorted(list(set(top_keywords)))
    
    @staticmethod
    def parse_cv(text: str) -> Dict:
        """Parse CV text and extract all relevant information."""
        return {
            'skills': CVParser.extract_skills(text),
            'tech_stack': CVParser.extract_tech_stack(text),
            'job_roles': CVParser.extract_job_roles(text),
            'experience_years': CVParser.extract_experience_years(text),
            'education': CVParser.extract_education(text),
            'certifications': CVParser.extract_certifications(text),
            'keywords': CVParser.extract_keywords(text),
            'parsed_at': datetime.utcnow().isoformat()
        }
