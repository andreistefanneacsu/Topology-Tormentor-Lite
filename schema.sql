CREATE EXTENSION IF NOT EXISTS pgcrypto;

DROP TABLE IF EXISTS submissions CASCADE;
DROP TABLE IF EXISTS exam_enrollments CASCADE;
DROP TABLE IF EXISTS module_enrollments CASCADE;
DROP TABLE IF EXISTS exams CASCADE;
DROP TABLE IF EXISTS laboratories CASCADE;
DROP TABLE IF EXISTS courses CASCADE;
DROP TABLE IF EXISTS module_professors CASCADE;
DROP TABLE IF EXISTS modules CASCADE;
DROP TABLE IF EXISTS students CASCADE;
DROP TABLE IF EXISTS professors CASCADE;
DROP TABLE IF EXISTS users CASCADE;

DROP TYPE IF EXISTS account_type_enum CASCADE;
DROP TYPE IF EXISTS account_status_enum CASCADE;
DROP TYPE IF EXISTS academic_title_enum CASCADE;
DROP TYPE IF EXISTS exam_type_enum CASCADE;
DROP TYPE IF EXISTS difficulty_level_enum CASCADE;
DROP TYPE IF EXISTS submission_status_enum CASCADE;

CREATE TYPE account_type_enum AS ENUM ('STUDENT', 'PROFESSOR', 'ADMIN', 'MODERATOR');
CREATE TYPE account_status_enum AS ENUM ('ACTIVE', 'SUSPENDED', 'GRADUATED');
CREATE TYPE academic_title_enum AS ENUM ('ASISTENT', 'LECTOR', 'CONFERENTIAR', 'PROFESOR');
CREATE TYPE exam_type_enum AS ENUM ('THEORY', 'PRACTICAL', 'MIXED');
CREATE TYPE difficulty_level_enum AS ENUM ('BEGINNER', 'INTERMEDIATE', 'ADVANCED');
CREATE TYPE submission_status_enum AS ENUM ('DRAFT', 'PENDING_REVIEW', 'GRADED');

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL CHECK (TRIM(first_name) <> ''),
    last_name VARCHAR(50) NOT NULL CHECK (TRIM(last_name) <> ''),
    email VARCHAR(100) UNIQUE NOT NULL CHECK (email ~* '^[A-Za-z0-9._+%-]+@[A-Za-z0-9.-]+[.][A-Za-z]+$'),
    password_hash VARCHAR(255) NOT NULL, 
    account_type account_type_enum NOT NULL,
    university VARCHAR(100),
    faculty VARCHAR(100),
    profile_picture_url VARCHAR(255),
    status account_status_enum DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE professors (
    user_id INT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    academic_title academic_title_enum NOT NULL,
    department VARCHAR(100) NOT NULL,
    ai_provider VARCHAR(50),
    ai_model VARCHAR(50),
    ai_api_key VARCHAR(255)
);

CREATE TABLE students (
    user_id INT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    enrollment_year INT NOT NULL,
    study_group VARCHAR(20) NOT NULL
);

CREATE TABLE modules (
    id SERIAL PRIMARY KEY,
    module_code VARCHAR(10) UNIQUE NOT NULL,
    title VARCHAR(150) NOT NULL UNIQUE,
    description TEXT,
    image_url VARCHAR(255),
    credits INT NOT NULL CHECK (credits > 0),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE module_professors (
    id SERIAL PRIMARY KEY,
    module_id INT NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    professor_id INT NOT NULL REFERENCES professors(user_id) ON DELETE CASCADE,
    is_coordinator BOOLEAN DEFAULT FALSE,
    UNIQUE (module_id, professor_id)
);

CREATE TABLE courses (
    id SERIAL PRIMARY KEY,
    module_id INT NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    title VARCHAR(150) NOT NULL,
    content TEXT NOT NULL,
    display_order INT NOT NULL CHECK (display_order > 0),
    UNIQUE (module_id, display_order)
);

CREATE TABLE laboratories (
    id SERIAL PRIMARY KEY,
    module_id INT NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    title VARCHAR(150) NOT NULL,
    instructions TEXT,
    starting_topology JSONB NOT NULL,
    goal_topology JSONB
);

CREATE TABLE module_enrollments (
    id SERIAL PRIMARY KEY,
    student_id INT NOT NULL REFERENCES students(user_id) ON DELETE CASCADE,
    module_id INT NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    enrolled_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (student_id, module_id)
);

CREATE TABLE exams (
    id SERIAL PRIMARY KEY,
    module_id INT NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    exam_type exam_type_enum NOT NULL,
    difficulty difficulty_level_enum DEFAULT 'INTERMEDIATE',
    title VARCHAR(150) NOT NULL,
    requirement_text TEXT NOT NULL,
    max_score DECIMAL(5,2) DEFAULT 10.00 CHECK (max_score > 0),
    passing_score DECIMAL(5,2) DEFAULT 5.00 CHECK (passing_score >= 0 AND passing_score <= max_score),
    starting_topology JSONB,
    goal_topology JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE exam_enrollments (
    id SERIAL PRIMARY KEY,
    student_id INT NOT NULL REFERENCES students(user_id) ON DELETE CASCADE,
    exam_id INT NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    enrolled_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (student_id, exam_id)
);

CREATE TABLE submissions (
    id SERIAL PRIMARY KEY,
    student_id INT NOT NULL REFERENCES students(user_id) ON DELETE CASCADE,
    exam_id INT NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    evaluator_id INT REFERENCES professors(user_id) ON DELETE SET NULL,
    answers_json JSONB,
    submitted_topology JSONB,
    grade DECIMAL(5,2) CHECK (grade >= 0),
    ai_feedback TEXT,
    status submission_status_enum DEFAULT 'PENDING_REVIEW',
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_module_professors_prof_id ON module_professors(professor_id);
CREATE INDEX idx_module_enrollments_student ON module_enrollments(student_id);
CREATE INDEX idx_exam_enrollments_student ON exam_enrollments(student_id);
CREATE INDEX idx_exams_module ON exams(module_id);
CREATE INDEX idx_submissions_exam_student ON submissions(exam_id, student_id);
CREATE INDEX idx_submissions_answers_json ON submissions USING GIN (answers_json);
CREATE INDEX idx_labs_topology_json ON laboratories USING GIN (starting_topology);

INSERT INTO users (first_name, last_name, email, password_hash, account_type, university, faculty) VALUES
('Super', 'Admin', 'admin@ttl.ro', crypt('Adm1n@TTL', gen_salt('bf')), 'ADMIN', 'UNIBUC', 'FMI'),
('Andrei-Cristian', 'Birlogeanu', 'andrei-cristian.birlogeanu@fmi.unibuc.ro', crypt('Pass123!', gen_salt('bf')), 'PROFESSOR', 'UNIBUC', 'FMI'),
('Andrei-Stefan', 'Neacsu', 'andrei-stefan.neacsu@fmi.unibuc.ro', crypt('Pass123!', gen_salt('bf')), 'PROFESSOR', 'UNIBUC', 'FMI'),
('Rebeca-Cristiana', 'Scarlat', 'rebeca-cristiana.scarlat@fmi.unibuc.ro', crypt('Pass123!', gen_salt('bf')), 'PROFESSOR', 'UNIBUC', 'FMI'),
('Alexandru', 'Gheorghe', 'alex.gheorghe@s.unibuc.ro', crypt('Pass123!', gen_salt('bf')), 'STUDENT', 'UNIBUC', 'FMI'),
('Ioana', 'Dumitru', 'ioana.dumitru@s.unibuc.ro', crypt('Pass123!', gen_salt('bf')), 'STUDENT', 'UNIBUC', 'FMI'),
('Andrei', 'Mihai', 'andrei.mihai@s.unibuc.ro', crypt('Pass123!', gen_salt('bf')), 'STUDENT', 'UNIBUC', 'FMI'),
('Elena', 'Stoica', 'elena.stoica@s.unibuc.ro', crypt('Pass123!', gen_salt('bf')), 'STUDENT', 'UNIBUC', 'FMI');

INSERT INTO professors (user_id, academic_title, department) VALUES
(1, 'PROFESOR', 'Informatica'),
(2, 'CONFERENTIAR', 'Informatica'),
(3, 'LECTOR', 'Informatica');

INSERT INTO students (user_id, enrollment_year, study_group) VALUES
(4, 2023, '261'),
(5, 2023, '262'),
(6, 2022, '263'),
(7, 2024, '264');

INSERT INTO modules (module_code, title, description, credits, image_url) VALUES
('NET101', 'TTL 1 - CCNA Introduction to Networks', 'Arhitecturi de retea, modelul OSI, stiva TCP/IP, configurare de baza a routerelor si switch-urilor.', 5, '/static/images/ccna.jpg'),
('NET201', 'TTL 2 - CCNA Routing & Switching', 'Concepte avansate de rutare (OSPF), switching (VLANs, STP), si protocoale de nivel retea.', 6, '/static/images/ccna.jpg'),
('SEC301', 'TTL 3 - Network Security', 'Criptografie, VPN-uri IPsec, firewall-uri, si bune practici de securizare a infrastructurii.', 4, '/static/images/sec.jpg');

INSERT INTO module_professors (module_id, professor_id, is_coordinator) VALUES
(1, 1, TRUE),
(1, 3, FALSE),
(2, 2, TRUE),
(3, 1, TRUE);

INSERT INTO courses (module_id, title, content, display_order) VALUES
(1, 'Capitolul 1: Modelul OSI si TCP/IP', 'Acest curs acopera teoria fundamentala a modelelor de referinta OSI si TCP/IP. \n\n1. Stratul Fizic (Cabluri, Fibra)\n2. Stratul Legatura de Date (MAC, Ethernet)\n3. Stratul Retea (IP, Rutare)\n4. Stratul Transport (TCP, UDP).', 1),
(1, 'Capitolul 2: Adresare IPv4 si Subnetting', 'Calculul subretelelor este esential. Vom folosi VLSM (Variable Length Subnet Mask) pentru a optimiza alocarea spatiului de adrese IP.', 2),
(1, 'Capitolul 3: Configurare Switch-uri', 'Invatam comenzile de baza Cisco IOS: enable, configure terminal, hostname, setarea parolelor.', 3),
(2, 'Capitolul 1: VLANs si Trunking', 'Crearea retelelor virtuale locale (VLAN) si configurarea porturilor Trunk folosind 802.1Q pentru a permite comunicarea inter-switch.', 1),
(2, 'Capitolul 2: OSPF Single-Area', 'Configurarea protocolului de rutare dinamica OSPFv2 intr-o singura arie (Area 0).', 2);

INSERT INTO laboratories (module_id, title, instructions, starting_topology) VALUES
(1, 'Lab 1 - Primul tau LAN', 'Seteaza IP-urile pe PC1 si PC2. Foloseste subnet-ul 192.168.1.0/24. Verifica conectivitatea folosind ping.', '{"devices": [{"id": 1, "type": "PC", "name": "PC-A", "ip": "192.168.1.10/24"}, {"id": 2, "type": "PC", "name": "PC-B"}], "links": [{"source": 1, "target": 2, "type": "Ethernet"}]}'::jsonb),
(1, 'Lab 2 - Parola pe Switch', 'Configureaza un hostname "SW1" si o parola enable secret "class".', '{"devices": [{"id": 1, "type": "Switch", "name": "Switch0"}], "links": []}'::jsonb),
(2, 'Lab 3 - Inter-VLAN Routing', 'Configureaza R1 cu subinterfete pentru VLAN 10 si VLAN 20 (Router on a stick).', '{"devices": [{"id": 1, "type": "Router", "name": "R1"}, {"id": 2, "type": "Switch", "name": "S1"}], "links": [{"source": 1, "target": 2, "type": "GigabitEthernet"}]}'::jsonb);

INSERT INTO module_enrollments (student_id, module_id) VALUES
(4, 1), (5, 1), (6, 1), (7, 1),
(4, 2), (6, 2);

INSERT INTO exams (module_id, exam_type, difficulty, title, requirement_text, max_score, passing_score, starting_topology) VALUES
(1, 'THEORY', 'BEGINNER', 'Midterm Grila NET101', 'Raspunde la urmatoarele intrebari despre OSI si Subnetting. Acest examen este de tip grila (multiple-choice).', 10.00, 5.00, '{"questions": [{"id": 1, "text": "Care strat al modelului OSI se ocupa cu rutarea pachetelor?", "options": ["Stratul Legatura de Date", "Stratul Retea", "Stratul Transport", "Stratul Prezentare"], "correct": 1}, {"id": 2, "text": "Care este masca de retea pentru prefixul /24?", "options": ["255.0.0.0", "255.255.0.0", "255.255.255.0", "255.255.255.128"], "correct": 2}, {"id": 3, "text": "Protocolul TCP garanteaza livrarea pachetelor?", "options": ["Da", "Nu"], "correct": 0}]}'::jsonb),
(2, 'PRACTICAL', 'INTERMEDIATE', 'Examen Practic Rutare Statica', 'Configureaza rutarea statica pe routerele R1 si R2 astfel incat PC1 sa poata comunica (face ping) cu PC2. Asigura-te ca adaugi si rutele de intors (return routes) corecte.', 10.00, 5.00, '{"devices": [{"id": 1, "type": "Router", "name": "R1"}, {"id": 2, "type": "Router", "name": "R2"}, {"id": 3, "type": "PC", "name": "PC1"}, {"id": 4, "type": "PC", "name": "PC2"}], "links": [{"source": 1, "target": 2, "type": "Serial"}, {"source": 3, "target": 1, "type": "Ethernet"}, {"source": 4, "target": 2, "type": "Ethernet"}]}'::jsonb),
(1, 'PRACTICAL', 'INTERMEDIATE', 'Examen Practic NET101', 'Configureaza PC1 si PC2 sa comunice. Adauga un switch.', 10.00, 5.00, '{"devices": [{"id": 1, "type": "PC", "name": "PC1"}, {"id": 2, "type": "PC", "name": "PC2"}], "links": []}'::jsonb),
(2, 'PRACTICAL', 'ADVANCED', 'Examen OSPF NET201', 'Configureaza OSPF Area 0 pe R1 si R2 conform cerintelor.', 10.00, 5.00, '{"devices": [{"id": 1, "type": "Router", "name": "R1"}, {"id": 2, "type": "Router", "name": "R2"}], "links": [{"source": 1, "target": 2, "type": "Serial"}]}'::jsonb);

INSERT INTO exam_enrollments (student_id, exam_id) VALUES 
(4, 1), (5, 1), (6, 1), (7, 1),
(4, 2), (5, 2),
(4, 3), (6, 3);

INSERT INTO submissions (student_id, exam_id, evaluator_id, answers_json, submitted_topology, grade, status) VALUES
(4, 2, 1, NULL, '{"devices": [{"id": 1, "type": "Router", "name": "R1", "configured": true}]}'::jsonb, 9.50, 'GRADED'),
(5, 2, NULL, NULL, '{"devices": [{"id": 1, "type": "Router", "name": "R1", "configured": false}]}'::jsonb, NULL, 'PENDING_REVIEW');