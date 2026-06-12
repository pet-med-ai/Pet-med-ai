# Automated Reminder Delivery Feature Flags V1

## Required flags

```txt
ENABLE_PREVENTIVE_AUTO_DELIVERY=false
ENABLE_PREVENTIVE_SMS_DELIVERY=false
ENABLE_PREVENTIVE_WECHAT_DELIVERY=false
ENABLE_PREVENTIVE_EMAIL_DELIVERY=false
ENABLE_PREVENTIVE_DELIVERY_DRY_RUN=true
ENABLE_PREVENTIVE_DELIVERY_MANUAL_APPROVAL=true
```

## Required behavior

### ENABLE_PREVENTIVE_AUTO_DELIVERY

```txt
default=false
global kill switch
must be false in production until approved pilot
```

### Channel flags

```txt
ENABLE_PREVENTIVE_SMS_DELIVERY=false
ENABLE_PREVENTIVE_WECHAT_DELIVERY=false
ENABLE_PREVENTIVE_EMAIL_DELIVERY=false
```

All channel flags must remain false until provider-specific risk review and sandbox validation pass.

### Dry-run flag

```txt
ENABLE_PREVENTIVE_DELIVERY_DRY_RUN=true
```

Dry-run may calculate eligibility and message preview.

Dry-run must not:

```txt
call provider send API
send SMS
send WeChat
send email
```

### Manual approval flag

```txt
ENABLE_PREVENTIVE_DELIVERY_MANUAL_APPROVAL=true
```

Manual approval means a human must approve a specific delivery attempt.

## Flag dependencies

Live delivery requires all:

```txt
ENABLE_PREVENTIVE_AUTO_DELIVERY=true
specific channel flag=true
ENABLE_PREVENTIVE_DELIVERY_MANUAL_APPROVAL=true for pilot
client consent valid
opt-out false
rate limit passed
quiet hours passed
template approved
```

## Validator expectations

Future validators must fail if:

```txt
auto delivery defaults to true
channel delivery defaults to true
dry-run sends external message
manual approval disabled during pilot
```
