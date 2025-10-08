import enum
import uuid
from sqlalchemy import (
    ARRAY,
    Column,
    Float,
    Integer,
    Interval,
    String,
    ForeignKey,
    Enum,
    Text,
    Date,
    Index,
    Time,
    UniqueConstraint,
    func,
    Boolean,
    LargeBinary,
)
from sqlalchemy.orm import declarative_base, relationship, Mapped
from sqlalchemy.sql.sqltypes import DateTime
from cor_pass.database.db import engine
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()


class Status(enum.Enum):
    premium: str = "premium"
    basic: str = "basic"


class Doctor_Status(enum.Enum):
    pending: str = "pending"
    approved: str = "approved"
    agreed: str = "agreed"
    rejected: str = "rejected"
    need_revision: str = "need_revision"


class AuthSessionStatus(enum.Enum):
    PENDING: str = "pending"
    APPROVED: str = "approved"
    REJECTED: str = "rejected"
    TIMEOUT: str = "timeout"


class PatientStatus(enum.Enum):
    registered = "registered"
    diagnosed = "diagnosed"
    under_treatment = "under_treatment"
    hospitalized = "hospitalized"
    discharged = "discharged"
    died = "died"
    in_process = "in_process"
    referred_for_additional_consultation = "referred_for_additional_consultation"


class PatientClinicStatus(enum.Enum):
    registered = "registered"
    diagnosed = "diagnosed"
    under_treatment = "under_treatment"
    hospitalized = "hospitalized"
    discharged = "discharged"
    died = "died"
    in_process = "in_process"
    referred_for_additional_consultation = "referred_for_additional_consultation"
    awaiting_report = "awaiting_report"
    completed = "completed"
    error = "error"


# Типы макроархива для параметров кейса
class MacroArchive(enum.Enum):
    ESS = "ESS - без залишку"
    RSS = "RSS - залишок"


# Типы декальцинации для параметров кейса
class DecalcificationType(enum.Enum):
    ABSENT = "Відсутня"
    EDTA = "EDTA"
    ACIDIC = "Кислотна"


# Типы образцов для параметров кейса
class SampleType(enum.Enum):
    NATIVE = "Нативний біоматеріал"
    BLOCKS = "Блоки/Скельця"


# Типы материалов (исследований) для параметров кейса
class MaterialType(enum.Enum):
    R = "Resectio"
    B = "Biopsy"
    E = "Excisio"
    C = "Cytology"
    CB = "Cellblock"
    S = "Second Opinion"
    A = "Autopsy"
    EM = "Electron Microscopy"
    OTHER = "Інше"


# Типы срочности для параметров кейса
class UrgencyType(enum.Enum):
    S = "Standard"
    U = "Urgent"
    F = "Frozen"


# Типы фиксации для параметров кейса
class FixationType(enum.Enum):
    NBF_10 = "10% NBF"
    OSMIUM = "Osmium"
    BOUIN = "Bouin"
    ALCOHOL = "Alcohol"
    GLUTARALDEHYDE_2 = "2% Glutaraldehyde"
    OTHER = "Інше"


# Типы исследований для направления
class StudyType(enum.Enum):
    CYTOLOGY = "Цитологія"
    HISTOPATHOLOGY = "Патогістологія"
    IMMUNOHISTOCHEMISTRY = "Імуногістохімія"
    FISH_CISH = "FISH/CISH"
    CB = "Cellblock"
    S = "Second Opinion"
    A = "Autopsy"
    EM = "Electron Microscopy"
    OTHER = "Інше"


# Типы окрашивания для стёкол
class StainingType(enum.Enum):
    HE = "H&E"
    ALCIAN_PAS = "Alcian PAS"
    CONGO_RED = "Congo red"
    MASSON_TRICHROME = "Masson Trichrome"
    VAN_GIESON = "van Gieson"
    ZIEHL_NEELSEN = "Ziehl Neelsen"
    WARTHIN_STARRY_SILVER = "Warthin-Starry Silver"
    GROCOTT_METHENAMINE_SILVER = "Grocott's Methenamine Silver"
    TOLUIDINE_BLUE = "Toluidine Blue"
    PERLS_PRUSSIAN_BLUE = "Perls Prussian Blue"
    PAMS = "PAMS"
    PICROSIRIUS = "Picrosirius"
    SIRIUS_RED = "Sirius red"
    THIOFLAVIN_T = "Thioflavin T"
    TRICHROME_AFOG = "Trichrome AFOG"
    VON_KOSSA = "von Kossa"
    GIEMSA = "Giemsa"
    OTHAR = "Othar"

    def abbr(self) -> str:
        """Возвращает сокращение для печати"""
        overrides = {
            "H&E": "H&E",
            "PAMS": "PAM",
            "Othar": "O",
        }
        if self.value in overrides:
            return overrides[self.value]

        parts = self.value.replace("-", " ").replace("'", "").split()
        abbr = "".join(word[0].upper() for word in parts)

        return abbr[:3]


class Grossing_status(enum.Enum):
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    CREATED = "CREATED"
    IN_SIGNING_STATUS = "IN_SIGNING_STATUS"


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    cor_id = Column(String(250), unique=True, nullable=True)
    email = Column(String(250), unique=True, nullable=False)
    backup_email = Column(String(250), unique=True, nullable=True)
    password = Column(String(250), nullable=False)
    last_password_change = Column(DateTime, server_default=func.now())
    access_token = Column(String(500), nullable=True)
    refresh_token = Column(String(500), nullable=True)
    recovery_code = Column(
        LargeBinary, nullable=True
    )  # Уникальный код восстановление пользователя
    is_active = Column(Boolean, default=True)
    account_status: Mapped[Enum] = Column(
        "status", Enum(Status), default=Status.basic
    )  # Статус аккаунта: базовый / премиум
    unique_cipher_key = Column(
        String(250), nullable=False
    )  # уникальный ключ шифрования конкретного пользователя, в базе в зашифрованном виде, шифруется с помошью AES key переменной окружения
    user_sex = Column(String(10), nullable=True)
    birth = Column(Integer, nullable=True)
    user_index = Column(
        Integer, unique=True, nullable=True
    )  # индекс пользователя, используется в создании cor_id
    created_at = Column(DateTime, nullable=False, default=func.now())

    # Связи
    user_records = relationship(
        "Record", back_populates="user", cascade="all, delete-orphan"
    )
    user_settings = relationship(
        "UserSettings", back_populates="user", cascade="all, delete-orphan"
    )
    user_otp = relationship("OTP", back_populates="user", cascade="all, delete-orphan")

    user_sessions = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )
    user_doctors = relationship(
        "Doctor", back_populates="user", cascade="all, delete-orphan"
    )

    patient = relationship("Patient", back_populates="user", uselist=False)

    devices = relationship("Device", back_populates="user")
    shared_devices = relationship(
        "DeviceAccess",
        foreign_keys="[DeviceAccess.granting_user_id]",
        back_populates="granting_user",
    )
    access_to_devices = relationship(
        "DeviceAccess",
        foreign_keys="[DeviceAccess.accessing_user_id]",
        back_populates="accessing_user",
    )
    profile = relationship(
        "Profile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    user_lab_assistants = relationship(
        "LabAssistant", back_populates="user", cascade="all, delete-orphan"
    )
    user_energy_managers = relationship(
        "EnergyManager", back_populates="user", cascade="all, delete-orphan"
    )
    user_lawyers = relationship(
        "Lawyer", back_populates="user", cascade="all, delete-orphan"
    )
    blood_pressure_measurements = relationship(
        "BloodPressureMeasurement", back_populates="user", cascade="all, delete-orphan"
    )
    ecg_measurements = relationship(
        "ECGMeasurement", back_populates="user", cascade="all, delete-orphan"
    )

    first_aid_kits = relationship(
    "FirstAidKit", back_populates="user", cascade="all, delete-orphan"
)
    medicine_schedules = relationship(
        "MedicineSchedule", back_populates="user", cascade="all, delete-orphan"
    )

    # Индексы
    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_cor_id", "cor_id"),
    )


class Doctor(Base):
    __tablename__ = "doctors"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doctor_id = Column(
        String(36), ForeignKey("users.cor_id"), unique=True, nullable=False
    )
    work_email = Column(String(250), unique=True, nullable=False)
    phone_number = Column(String(20), nullable=True)
    first_name = Column(String(100), nullable=True)
    middle_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    doctors_photo = Column(LargeBinary, nullable=True)
    scientific_degree = Column(String(100), nullable=True)
    date_of_last_attestation = Column(Date, nullable=True)
    status = Column(Enum(Doctor_Status), default=Doctor_Status.pending, nullable=False)
    passport_code = Column(String(20), nullable=True)
    taxpayer_identification_number = Column(String(20), nullable=True)
    reserv_scan_data = Column(LargeBinary, nullable=True)
    reserv_scan_file_type = Column(String, nullable=True)
    date_of_next_review = Column(Date, nullable=True)
    place_of_registration = Column(String, nullable=True)

    user = relationship("User", back_populates="user_doctors")
    diplomas = relationship(
        "Diploma", back_populates="doctor", cascade="all, delete-orphan"
    )
    certificates = relationship(
        "Certificate", back_populates="doctor", cascade="all, delete-orphan"
    )
    clinic_affiliations = relationship(
        "ClinicAffiliation", back_populates="doctor", cascade="all, delete-orphan"
    )
    patient_statuses = relationship(
        "DoctorPatientStatus", back_populates="doctor", cascade="all, delete-orphan"
    )
    signatures = relationship(
        "DoctorSignature", back_populates="doctor", cascade="all, delete-orphan"
    )
    doctor_diagnoses = relationship("DoctorDiagnosis", back_populates="doctor")
    signed_diagnoses = relationship("ReportSignature", back_populates="doctor")
    owned_cases = relationship("Case", back_populates="owner_obj")


class LabAssistant(Base):
    __tablename__ = "lab_assistants"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lab_assistant_cor_id = Column(
        String(36), ForeignKey("users.cor_id"), unique=True, nullable=False
    )
    first_name = Column(String(100), nullable=True)
    surname = Column(String(100), nullable=True)
    middle_name = Column(String(100), nullable=True)
    lab_assistants_photo = Column(LargeBinary, nullable=True)

    user = relationship("User", back_populates="user_lab_assistants")


class EnergyManager(Base):
    __tablename__ = "energy_managers"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    energy_manager_cor_id = Column(
        String(36), ForeignKey("users.cor_id"), unique=True, nullable=False
    )
    first_name = Column(String(100), nullable=True)
    surname = Column(String(100), nullable=True)
    middle_name = Column(String(100), nullable=True)
    lab_assistants_photo = Column(LargeBinary, nullable=True)

    user = relationship("User", back_populates="user_energy_managers")


class Lawyer(Base):
    __tablename__ = "lawyers"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lawyer_cor_id = Column(
        String(36), ForeignKey("users.cor_id"), unique=True, nullable=False
    )
    first_name = Column(String(100), nullable=True)
    surname = Column(String(100), nullable=True)
    middle_name = Column(String(100), nullable=True)

    user = relationship("User", back_populates="user_lawyers")


class Diploma(Base):
    __tablename__ = "diplomas"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doctor_id = Column(String(36), ForeignKey("doctors.doctor_id"), nullable=False)
    file_data = Column(LargeBinary, nullable=True)
    file_type = Column(String, nullable=True)
    date = Column(Date, nullable=False)
    series = Column(String(50), nullable=False)
    number = Column(String(50), nullable=False)
    university = Column(String(250), nullable=False)

    doctor = relationship("Doctor", back_populates="diplomas")


class Certificate(Base):
    __tablename__ = "certificates"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doctor_id = Column(String(36), ForeignKey("doctors.doctor_id"), nullable=False)
    file_data = Column(LargeBinary, nullable=True)
    file_type = Column(String, nullable=True)
    date = Column(Date, nullable=False)
    series = Column(String(50), nullable=False)
    number = Column(String(50), nullable=False)
    university = Column(String(250), nullable=False)

    doctor = relationship("Doctor", back_populates="certificates")


class ClinicAffiliation(Base):
    __tablename__ = "clinic_affiliations"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doctor_id = Column(String(36), ForeignKey("doctors.doctor_id"), nullable=False)
    clinic_name = Column(String(250), nullable=False)
    department = Column(String(250), nullable=True)
    position = Column(String(250), nullable=True)
    specialty = Column(String(250), nullable=True)

    doctor = relationship("Doctor", back_populates="clinic_affiliations")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.cor_id"), nullable=False)
    device_type = Column(String(250), nullable=True)
    device_info = Column(String(250), nullable=True)
    app_id = Column(String(250), nullable=True) # Идентификатор апки
    device_id = Column(String(250), nullable=True) # айди устройства
    ip_address = Column(String(250), nullable=True)
    device_os = Column(String(250), nullable=True)
    jti = Column(
        String,
        unique=True,
        nullable=True,
        comment="JTI последнего Access токена, выданного для этой сессии",
    )
    refresh_token = Column(LargeBinary, nullable=True)
    access_token = Column(LargeBinary, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )

    # Связи
    user = relationship("User", back_populates="user_sessions")

    # Индексы
    __table_args__ = (
        Index("idx_user_sessions_user_id", "user_id"),
    )


class CorIdAuthSession(Base):
    __tablename__ = "cor_id_auth_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), index=True, nullable=True)
    cor_id = Column(String(250), index=True, nullable=True)
    session_token = Column(String(36), unique=True, index=True, nullable=False)
    app_id = Column(String(250), nullable=True)
    device_id = Column(String(250), nullable=True)
    status = Column(
        Enum(AuthSessionStatus), default=AuthSessionStatus.PENDING, nullable=False
    )
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())

    __table_args__ = (Index("idx_cor_id_auth_sessions_token", "session_token"),)


class Verification(Base):
    __tablename__ = "verification"
    id = Column(Integer, primary_key=True)
    email = Column(String(250), unique=True, nullable=False)
    verification_code = Column(Integer, default=None)
    email_confirmation = Column(Boolean, default=False)

    # Индексы
    __table_args__ = (Index("idx_verification_email", "email"),)


class Record(Base):
    __tablename__ = "records"

    record_id = Column(Integer, primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    record_name = Column(String(250), nullable=False)
    website = Column(String(250), nullable=True)
    username = Column(LargeBinary, nullable=True)
    password = Column(LargeBinary, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    edited_at = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )
    notes = Column(Text, nullable=True)
    is_favorite = Column(Boolean, default=False, nullable=True)

    # Связи
    user = relationship("User", back_populates="user_records")
    tags = relationship("Tag", secondary="records_tags")

    # Индексы
    __table_args__ = (Index("idx_records_user_id", "user_id"),)


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)

    # Индексы
    __table_args__ = (Index("idx_tags_name", "name"),)


class RecordTag(Base):
    __tablename__ = "records_tags"

    record_id = Column(Integer, ForeignKey("records.record_id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id"), primary_key=True)


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id = Column(
        String(36), ForeignKey("users.id"), nullable=False, primary_key=True
    )
    local_password_storage = Column(Boolean, default=False)
    cloud_password_storage = Column(Boolean, default=True)
    local_medical_storage = Column(Boolean, default=False)
    cloud_medical_storage = Column(Boolean, default=True)

    # Связи
    user = relationship("User", back_populates="user_settings")


class OTP(Base):
    __tablename__ = "otp_records"

    record_id = Column(Integer, primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    record_name = Column(String(250), nullable=False)
    username = Column(String(250), nullable=True)
    private_key = Column(LargeBinary, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    edited_at = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )

    # Связи
    user = relationship("User", back_populates="user_otp")

    # Индексы
    __table_args__ = (Index("idx_otp_records_user_id", "user_id"),)


class Patient(Base):
    __tablename__ = "patients"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    patient_cor_id = Column(
        String(250), unique=True, nullable=False
    )  # Теперь пациентский кор айди просто строковое поле
    user_id = Column(
        String(36), ForeignKey("users.id"), unique=True, nullable=True
    )  # новый необязательный внешний ключ для юзера

    encrypted_surname = Column(LargeBinary, nullable=True)  # Зашифрована фамилия
    encrypted_first_name = Column(LargeBinary, nullable=True)  # Зашифрованное имя
    encrypted_middle_name = Column(
        LargeBinary, nullable=True
    )  # Зашифрованное отчество (может быть null)
    birth_date = Column(Date, nullable=True)
    sex = Column(String(10), nullable=True)
    email = Column(String(250), nullable=True)
    phone_number = Column(String(20), nullable=True)
    address = Column(String(500), nullable=True)
    photo = Column(LargeBinary, nullable=True)  # Хранение фото как бинарные данные
    change_date = Column(DateTime, default=func.now(), onupdate=func.now())
    create_date = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="patient")
    doctor_statuses = relationship("DoctorPatientStatus", back_populates="patient")
    clinic_statuses = relationship("PatientClinicStatusModel", back_populates="patient")

    search_tokens = Column(Text, default="", nullable=False)

    def __repr__(self):
        return f"<Patient(id='{self.id}', patient_cor_id='{self.patient_cor_id}')>"


class PatientClinicStatusModel(Base):
    __tablename__ = "clinic_patient_statuses"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False)
    patient_status_for_clinic = Column(
        Enum(PatientClinicStatus), default=PatientClinicStatus.registered
    )
    assigned_date = Column(DateTime, default=func.now())
    updated_date = Column(DateTime, default=func.now(), onupdate=func.now())

    patient = relationship("Patient", back_populates="clinic_statuses")


class DoctorPatientStatus(Base):
    __tablename__ = "doctor_patient_statuses"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(String(36), ForeignKey("doctors.id"), nullable=False)
    status = Column(Enum(PatientStatus), nullable=False)
    assigned_date = Column(DateTime, default=func.now())
    updated_date = Column(DateTime, default=func.now(), onupdate=func.now())

    patient = relationship("Patient", back_populates="doctor_statuses")
    doctor = relationship("Doctor", back_populates="patient_statuses")

    __table_args__ = (
        # Каждый врач имеет только 1 конкретный статус под пациента
        UniqueConstraint(
            "patient_id", "doctor_id", name="unique_patient_doctor_status"
        ),
    )


# Кейс
class Case(Base):
    __tablename__ = "cases"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id = Column(String(36), index=True)
    creation_date = Column(DateTime, default=func.now())
    case_code = Column(String(250), index=True, unique=True)
    bank_count = Column(Integer, default=0)
    cassette_count = Column(Integer, default=0)
    glass_count = Column(Integer, default=0)
    grossing_status = Column(Enum(Grossing_status), default=Grossing_status.CREATED)
    pathohistological_conclusion = Column(Text, nullable=True)
    microdescription = Column(Text, nullable=True)
    general_macrodescription = Column(Text, nullable=True)
    case_owner = Column(String(36), ForeignKey("doctors.doctor_id"), nullable=True)
    closing_date = Column(DateTime, nullable=True)
    is_printed_cassette = Column(Boolean, nullable=True, default=False)
    is_printed_glass = Column(Boolean, nullable=True, default=False)
    is_printed_qr = Column(Boolean, nullable=True, default=False)

    samples = relationship(
        "Sample", back_populates="case", cascade="all, delete-orphan"
    )
    referral = relationship(
        "Referral", back_populates="case", cascade="all, delete-orphan"
    )
    case_parameters = relationship(
        "CaseParameters",
        uselist=False,
        back_populates="case",
        cascade="all, delete-orphan",
    )
    report = relationship(
        "Report", back_populates="case", uselist=False, cascade="all, delete-orphan"
    )
    owner_obj = relationship(
        "Doctor", back_populates="owned_cases", foreign_keys=[case_owner]
    )


# Банка
class Sample(Base):
    __tablename__ = "samples"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False)
    sample_number = Column(String(50))
    cassette_count = Column(Integer, default=0)
    glass_count = Column(Integer, default=0)
    archive = Column(Boolean, default=False)
    macro_description = Column(Text, nullable=True)
    is_printed_cassette = Column(Boolean, nullable=True, default=False)
    is_printed_glass = Column(Boolean, nullable=True, default=False)

    case = relationship("Case", back_populates="samples")
    cassette = relationship(
        "Cassette", back_populates="sample", cascade="all, delete-orphan"
    )


# Касета
class Cassette(Base):
    __tablename__ = "cassettes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sample_id = Column(String(36), ForeignKey("samples.id"), nullable=False)
    cassette_number = Column(
        String(50)
    )  # Порядковый номер кассеты в рамках конкретной банки
    comment = Column(String(500), nullable=True)
    glass_count = Column(Integer, default=0)
    is_printed = Column(Boolean, nullable=True, default=False)
    glass = relationship(
        "Glass", back_populates="cassette", cascade="all, delete-orphan"
    )
    sample = relationship("Sample", back_populates="cassette")


# Стекло
class Glass(Base):
    __tablename__ = "glasses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    cassette_id = Column(String(36), ForeignKey("cassettes.id"), nullable=False)
    glass_number = Column(Integer)  # Порядковый номер стекла
    staining = Column(Enum(StainingType), nullable=True)
    glass_data = Column(LargeBinary, nullable=True)
    is_printed = Column(Boolean, nullable=True, default=False)
    scan_url = Column(String, nullable=True)
    preview_url = Column(String, nullable=True)
    cassette = relationship("Cassette", back_populates="glass")


# Параметры кейса
class CaseParameters(Base):
    __tablename__ = "case_parameters"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id"), unique=True, nullable=False)
    macro_archive = Column(Enum(MacroArchive), default=MacroArchive.ESS)
    decalcification = Column(
        Enum(DecalcificationType), default=DecalcificationType.ABSENT
    )
    sample_type = Column(Enum(SampleType), default=SampleType.NATIVE)
    material_type = Column(Enum(MaterialType), default=MaterialType.B)
    urgency = Column(Enum(UrgencyType), default=UrgencyType.S)
    container_count_actual = Column(Integer, nullable=True)
    fixation = Column(Enum(FixationType), default=FixationType.NBF_10)
    macro_description = Column(Text, nullable=True)

    case = relationship("Case", back_populates="case_parameters")


# Направление на исследование
class Referral(Base):
    __tablename__ = "referrals"

    id = Column(
        String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4())
    )
    case_id = Column(
        String,
        ForeignKey("cases.id"),
        unique=True,
        nullable=False,
        comment="ID связанного кейса",
    )
    case_number = Column(String, index=True, nullable=False, comment="Номер кейса")
    created_at = Column(
        DateTime, default=func.now(), comment="Дата создания направления"
    )
    research_type = Column(Enum(StudyType), nullable=True, comment="Вид исследования")
    container_count = Column(
        Integer, nullable=True, comment="Фактическое количество контейнеров"
    )
    medical_card_number = Column(String, nullable=True, comment="Номер медкарты")
    clinical_data = Column(Text, nullable=True, comment="Клинические данные")
    clinical_diagnosis = Column(String, nullable=True, comment="Клинический диагноз")
    medical_institution = Column(
        String, nullable=True, comment="Медицинское учреждение"
    )
    department = Column(String, nullable=True, comment="Отделение")
    attending_doctor = Column(String, nullable=True, comment="Лечащий врач")
    doctor_contacts = Column(String, nullable=True, comment="Контакты врача")
    medical_procedure = Column(String, nullable=True, comment="Медицинская процедура")
    final_report_delivery = Column(
        Text, nullable=True, comment="Финальный репорт отправить"
    )
    issued_at = Column(DateTime, nullable=True, comment="Выдано (дата)")
    biomaterial_date = Column(
        DateTime, nullable=True, comment="Дата забора биоматериала"
    )

    case = relationship("Case", back_populates="referral")

    attachments = relationship(
        "ReferralAttachment",
        back_populates="referral",
        cascade="all, delete-orphan",
        lazy="joined",
    )


class ReferralAttachment(Base):
    __tablename__ = "referral_attachments"

    id = Column(
        String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4())
    )
    referral_id = Column(
        String,
        ForeignKey("referrals.id"),
        nullable=False,
        comment="ID связанного направления",
    )
    filename = Column(String, nullable=False, comment="Имя файла")
    content_type = Column(
        String,
        nullable=False,
        comment="Тип содержимого (например, image/jpeg, application/pdf)",
    )
    file_data = Column(LargeBinary, nullable=False, comment="Бинарные данные файла")

    referral = relationship("Referral", back_populates="attachments")


# Модели для девайсов


class DeviceStatus(enum.Enum):
    MANUFACTURED = "manufactured"
    ACTIVATED = "activated"
    BLOCKED = "blocked"


class ManufacturedDevice(Base):
    __tablename__ = "manufactured_devices"

    id = Column(
        String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4())
    )
    token = Column(String, unique=True, index=True)
    serial_number = Column(String, unique=True)
    status = Column(Enum(DeviceStatus), default=DeviceStatus.MANUFACTURED)


class Device(Base):
    __tablename__ = "devices"

    id = Column(
        String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4())
    )
    token = Column(
        String, unique=True, index=True
    )  # JWT токен, которые выдается устройству после привязки
    name = Column(String(250))
    create_date = Column(DateTime, default=func.now())
    user_id = Column(String, ForeignKey("users.cor_id"))
    serial_number = Column(String, ForeignKey("manufactured_devices.serial_number"))

    user = relationship("User", back_populates="devices")
    device = relationship("ManufacturedDevice")


class AccessLevel(enum.Enum):
    READ = "read"
    READ_WRITE = "read_write"
    SHARE = "share"


class DeviceAccess(Base):
    __tablename__ = "device_access"

    id = Column(
        String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4())
    )
    device_id = Column(String, ForeignKey("devices.id"))
    granting_user_id = Column(String, ForeignKey("users.cor_id"))
    accessing_user_id = Column(String, ForeignKey("users.cor_id"))
    access_level = Column(Enum(AccessLevel), default=AccessLevel.READ)
    create_date = Column(DateTime, default=func.now())

    device = relationship("Device")
    granting_user = relationship(
        "User", foreign_keys=[granting_user_id], back_populates="shared_devices"
    )
    accessing_user = relationship(
        "User", foreign_keys=[accessing_user_id], back_populates="access_to_devices"
    )


class PrintingDevice(Base):
    __tablename__ = "printing_device"

    id = Column(
        String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4())
    )
    device_class = Column(String, nullable=False)
    device_identifier = Column(String, nullable=False, unique=True)
    subnet_mask = Column(String, nullable=True)
    gateway = Column(String, nullable=True)
    ip_address = Column(String, nullable=False)
    port = Column(Integer, nullable=True)
    comment = Column(String, nullable=True)
    location = Column(String, nullable=True)


class Profile(Base):
    __tablename__ = "profiles"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, nullable=False)

    encrypted_surname = Column(LargeBinary, nullable=True)
    encrypted_first_name = Column(LargeBinary, nullable=True)
    encrypted_middle_name = Column(LargeBinary, nullable=True)

    birth_date = Column(Date, nullable=True)
    phone_number = Column(String(20), nullable=True)
    city = Column(String(100), nullable=True)

    car_brand = Column(String(100), nullable=True)
    engine_type = Column(String(50), nullable=True)
    fuel_tank_volume = Column(Integer, nullable=True)

    photo_data = Column(LargeBinary, nullable=True)
    photo_file_type = Column(String, nullable=True)

    change_date = Column(DateTime, default=func.now(), onupdate=func.now())
    create_date = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="profile")

    def __repr__(self):
        return f"<Profile(id='{self.id}', user_id='{self.user_id}')>"


class DoctorSignature(Base):
    __tablename__ = "doctor_signatures"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doctor_id = Column(String(36), ForeignKey("doctors.id"), nullable=False)
    signature_name = Column(String(255), nullable=True)
    signature_scan_data = Column(LargeBinary, nullable=True)
    signature_scan_type = Column(String, nullable=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

    # Связи
    doctor = relationship("Doctor", back_populates="signatures")


class ReportSignature(Base):
    __tablename__ = "report_signatures"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    diagnosis_entry_id = Column(
        String(36), ForeignKey("doctor_diagnoses.id"), nullable=True, unique=True
    )
    doctor_id = Column(String(36), ForeignKey("doctors.id"), nullable=False)
    doctor_signature_id = Column(
        String(36), ForeignKey("doctor_signatures.id"), nullable=True
    )
    signed_at = Column(DateTime, default=func.now())

    # Связи
    doctor_diagnosis_entry = relationship("DoctorDiagnosis", back_populates="signature")
    doctor = relationship("Doctor")
    doctor_signature = relationship("DoctorSignature")


class Report(Base):
    __tablename__ = "reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id"), unique=True, nullable=False)
    attached_glass_ids = Column(ARRAY(String(36)), nullable=True, default=[])
    # Связи
    case = relationship("Case", back_populates="report")
    doctor_diagnoses = relationship(
        "DoctorDiagnosis",
        back_populates="report",
        order_by="DoctorDiagnosis.created_at",
    )


class DoctorDiagnosis(Base):
    __tablename__ = "doctor_diagnoses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id = Column(String(36), ForeignKey("reports.id"), nullable=False)
    doctor_id = Column(String(36), ForeignKey("doctors.doctor_id"), nullable=False)
    created_at = Column(DateTime, default=func.now())

    immunohistochemical_profile = Column(Text, nullable=True)
    molecular_genetic_profile = Column(Text, nullable=True)
    pathomorphological_diagnosis = Column(Text, nullable=True)

    icd_code = Column(String(50), nullable=True)
    comment = Column(Text, nullable=True)

    report_macrodescription = Column(Text, nullable=True)
    report_microdescription = Column(Text, nullable=True)

    # Связи
    report = relationship("Report", back_populates="doctor_diagnoses")
    doctor = relationship("Doctor")
    signature = relationship(
        "ReportSignature", uselist=False, back_populates="doctor_diagnosis_entry"
    )


class BloodPressureMeasurement(Base):
    __tablename__ = "blood_pressure_measurements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    systolic_pressure = Column(
        Integer, nullable=False, comment="Систолическое (верхнее) артериальное давление"
    )
    diastolic_pressure = Column(
        Integer, nullable=False, comment="Диастолическое (нижнее) артериальное давление"
    )
    pulse = Column(
        Integer, nullable=False, comment="Частота сердечных сокращений (пульс)"
    )

    measured_at = Column(
        DateTime,
        nullable=False,
        comment="Дата и время измерения, полученное с устройства",
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        comment="Дата и время сохранения записи в БД",
    )
    user = relationship("User", back_populates="blood_pressure_measurements")

    __table_args__ = (
        Index("idx_bpm_user_id", "user_id"),
        Index("idx_bpm_measured_at", "measured_at"),
    )


class EnergeticObject(Base):
    __tablename__ = "energetic_objects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True, comment="Имя/название объекта")
    description = Column(String, nullable=True, comment="Описание объекта")

    modbus_registers = Column(
        JSONB,
        nullable=True,
        comment="Карта регистров Modbus (динамическая структура в формате JSON)"
    )
    is_active = Column(Boolean, default=False, comment="Активен ли фоновый опрос")

    # связи
    measurements = relationship("CerboMeasurement", back_populates="energetic_object", cascade="all, delete-orphan")
    schedules = relationship("EnergeticSchedule", back_populates="energetic_object", cascade="all, delete-orphan")

    # def __repr__(self):
    #     return f"<EnergeticObject(id={self.id}, name='{self.name}')>"


class CerboMeasurement(Base):
    __tablename__ = "cerbo_measurements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    energetic_object_id = Column(
        String(36), ForeignKey("energetic_objects.id"), nullable=False, index=True
    )
    created_at = Column(DateTime, nullable=False, default=func.now())
    measured_at = Column(DateTime, nullable=False, comment="Дата и время измерения")

    object_name: Column[str] = Column(String, nullable=True, index=True)

    # Данные из battery_status
    general_battery_power: Column[float] = Column(Float, nullable=False)

    # Данные из inverter_power_status
    inverter_total_ac_output: Column[float] = Column(Float, nullable=False)

    # Данные из ess_ac_status
    ess_total_input_power: Column[float] = Column(Float, nullable=False)

    # Данные из solarchargers_status
    solar_total_pv_power: Column[float] = Column(Float, nullable=False)

    soc: Column[float] = Column(Float, nullable=True)

    energetic_object = relationship("EnergeticObject", back_populates="measurements")





    def __repr__(self):
        return (
            f"<CerboMeasurement(id={self.id}, measured_at='{self.measured_at}', "
            f"object_name='{self.object_name}', general_battery_power={self.general_battery_power})>"
        )


class EnergeticSchedule(Base):
    __tablename__ = "energetic_schedule"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    energetic_object_id = Column(
        String(36), ForeignKey("energetic_objects.id"), nullable=False, index=True
    )

    # Параметры времени
    start_time = Column(Time, nullable=False, comment="Время начала работы режима (ЧЧ:ММ)")
    duration = Column(Interval, nullable=False, comment="Продолжительность режима")
    end_time = Column(Time, nullable=False, comment="Время окончания работы режима")

    # Параметры работы инвертора
    grid_feed_w = Column(Integer, nullable=False, comment="Отдача в сеть (Вт)")
    battery_level_percent = Column(Integer, nullable=False, comment="Целевой уровень батареи (%)")

    # Статусы расписания
    is_active = Column(Boolean, nullable=False, default=False)
    is_manual_mode = Column(Boolean, nullable=False, default=False)
    charge_battery_value = Column(Integer, nullable=False, default=300)

    energetic_object = relationship("EnergeticObject", back_populates="schedules")

    def __repr__(self):
        return (
            f"<EnergeticSchedule(id='{self.id}', start_time={self.start_time}, "
            f"duration={self.duration}, end_time={self.end_time}, "
            f"grid_feed_w={self.grid_feed_w}, battery_level_percent={self.battery_level_percent}, "
            f"charge_battery_value={self.charge_battery_value}, is_active={self.is_active}, "
            f"is_manual_mode={self.is_manual_mode})>"
        )



class ECGMeasurement(Base):
    __tablename__ = "ecg_measurements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        comment="Дата и время сохранения записи в БД",
    )
    file_data = Column(LargeBinary, nullable=False) 
    file_name = Column(String, nullable=True) 

    user = relationship("User", back_populates="ecg_measurements")


class DoctorSignatureSession(Base):
    __tablename__ = "doctor_signature_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_token = Column(String, unique=True, nullable=False)
    doctor_cor_id = Column(String(36), nullable=False)
    diagnosis_id = Column(String(36), nullable=False)
    doctor_signature_id = Column(String(36), nullable=True)
    status = Column(String, default="pending")  # pending/approved/rejected/expired
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime,nullable=False,default=func.now())



# Аптечка

class FirstAidKit(Base):
    __tablename__ = "first_aid_kits"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    user_cor_id = Column(String(36), ForeignKey("users.cor_id", ondelete="CASCADE"), nullable=False)

    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())


    medicines = relationship(
        "FirstAidKitItem", back_populates="first_aid_kit", cascade="all, delete-orphan"
    )
    user = relationship("User", back_populates="first_aid_kits")


    __table_args__ = (Index("idx_first_aid_kits_user_cor_id", "user_cor_id"),)


# Лекарство

class Medicine(Base):
    __tablename__ = "medicines"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    active_substance = Column(String(255), nullable=True)

    intake_method = Column(String(100), nullable=True)  # перорально, подкожно и т.д.

    # Разные типы параметров в зависимости от метода
    dosage = Column(Float, nullable=True)        # для перорального
    unit = Column(String(50), nullable=True)     # мг, мл и т.д.
    concentration = Column(Float, nullable=True) # для мазей и растворов
    volume = Column(Float, nullable=True)        # для растворов

    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    created_by = Column(String(100), nullable=False)


    schedules = relationship(
        "MedicineSchedule", back_populates="medicine", cascade="all, delete-orphan"
    )
    first_aid_kits = relationship(
        "FirstAidKitItem", back_populates="medicine", cascade="all, delete-orphan"
    )


    __table_args__ = (Index("idx_medicines_name", "name"),)


# Наполнение аптечки

class FirstAidKitItem(Base):
    __tablename__ = "first_aid_kit_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    first_aid_kit_id = Column(
        String(36), ForeignKey("first_aid_kits.id", ondelete="CASCADE"), nullable=False
    )
    medicine_id = Column(
        String(36), ForeignKey("medicines.id", ondelete="CASCADE"), nullable=False
    )
    quantity = Column(Integer, default=1, nullable=False)
    expiration_date = Column(Date, nullable=True)

    created_at = Column(DateTime, nullable=False, default=func.now())


    first_aid_kit = relationship("FirstAidKit", back_populates="medicines")
    medicine = relationship("Medicine", back_populates="first_aid_kits")


    __table_args__ = (
        Index("idx_first_aid_kit_items_kit_id", "first_aid_kit_id"),
        Index("idx_first_aid_kit_items_medicine_id", "medicine_id"),
    )


# Расписание приема

class MedicineSchedule(Base):
    __tablename__ = "medicine_schedules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    medicine_id = Column(
        String(36), ForeignKey("medicines.id", ondelete="CASCADE"), nullable=False
    )
    user_cor_id = Column(String(36), ForeignKey("users.cor_id", ondelete="CASCADE"), nullable=False)

    start_date = Column(Date, nullable=False)
    duration_days = Column(Integer, nullable=True)
    times_per_day = Column(Integer, nullable=True)
    intake_times = Column(JSONB, nullable=True)
    interval_minutes = Column(Integer, nullable=True)
    symptomatically = Column(Boolean, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())


    medicine = relationship("Medicine", back_populates="schedules")
    user = relationship("User", back_populates="medicine_schedules")

    __table_args__ = (
        Index("idx_medicine_schedules_user_cor_id", "user_cor_id"),
        Index("idx_medicine_schedules_medicine_id", "medicine_id"),
    )


class OphthalmologicalPrescription(Base):
    __tablename__ = "ophthalmological_prescription"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id = Column(String(36), index=True)
    
    # OD
    od_sph = Column(Float, nullable=False)
    od_cyl = Column(Float, nullable=False)
    od_ax = Column(Float, nullable=False)
    od_prism = Column(Float, nullable=False)
    od_base = Column(String(50), nullable=False)
    od_add = Column(Float, nullable=False)


    # OS
    os_sph = Column(Float, nullable=False)
    os_cyl = Column(Float, nullable=False)
    os_ax = Column(Float, nullable=False)
    os_prism = Column(Float, nullable=False)
    os_base = Column(String(50), nullable=False)
    os_add = Column(Float, nullable=False)

    glasses_purpose = Column(String(50), nullable=False)
    glasses_type = Column(String(50), nullable=False)

    created_at = Column(DateTime, nullable=False, default=func.now())
    expires_at = Column(DateTime, nullable=False, default=func.now())

    note = Column(String(350), nullable=False)




class ReportSignature(Base):
    __tablename__ = "ophthalmological_prescription_signature"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ophthalmological_prescription_id = Column(
        String(36), ForeignKey("ophthalmological_prescription.id"), nullable=True, unique=True
    )
    doctor_id = Column(String(36), ForeignKey("doctors.id"), nullable=False)
    doctor_signature_id = Column(
        String(36), ForeignKey("doctor_signatures.id"), nullable=True
    )
    signed_at = Column(DateTime, default=func.now())

    # Связи
    # doctor_diagnosis_entry = relationship("DoctorDiagnosis", back_populates="signature")
    # doctor = relationship("Doctor")
    # doctor_signature = relationship("DoctorSignature")

# Base.metadata.create_all(bind=engine)
