from pydantic import BaseModel, EmailStr, root_validator

class UserSignup(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: str

    @root_validator(pre=True)
    def all_fields_mandatory(cls, values):
        required_fields = ['email', 'username', 'password', 'full_name']
        errors = []
        for field in required_fields:
            if field not in values or not values[field]:
                # Store clear error strings
                errors.append(f"{field.replace('_', ' ').capitalize()} is required")
        if errors:
            # Join all in one and raise one ValueError (v2 limitation workaround)
            raise ValueError(", ".join(errors))
        return values
