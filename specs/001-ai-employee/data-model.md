# AI Employee Data Models

This document defines comprehensive data models for the Autonomous AI Employee system, designed for small business scale (1-10 employees, <100 transactions/month).

---

## 1. Core Entities

### 1.1 ActionItem

Represents a task detected from external sources (email, file drop, WhatsApp, etc.) that requires processing.

```typescript
interface ActionItem {
  // Identifiers
  id: string;                    // UUID v4
  source_type: SourceType;       // Origin of the item
  source_identifier: string;      // Email message-ID, file path, or external ID
  content_hash: string;          // SHA-256 hash for deduplication

  // Timestamps
  created_at: string;            // ISO 8601
  updated_at: string;            // ISO 8601
  due_date?: string;             // ISO 8601, optional deadline
  completed_at?: string;         // ISO 8601, when fully resolved

  // Content
  title: string;                 // Brief summary (max 200 chars)
  content: string;               // Full content/body
  priority: Priority;            // Processing priority
  category: string;               // Business category
  tags: string[];                // Array of tags for filtering

  // State
  status: ActionItemStatus;      // Current processing state
  assigned_to?: string;          // Agent or human responsible
  parent_id?: string;            // For sub-tasks, references parent ActionItem

  // Source metadata
  metadata: {
    sender?: string;             // Email sender or file source
    recipient?: string;          // Intended recipient
    subject?: string;            // Email subject or file name
    attachments?: Attachment[];   // List of attached files
    keywords?: string[];          // Detected keywords for routing
    sentiment?: 'positive' | 'negative' | 'neutral';
  };
}

type SourceType = 'email' | 'whatsapp' | 'file_drop' | 'scheduled' | 'manual';
type Priority = 'urgent' | 'high' | 'medium' | 'low';
type ActionItemStatus =
  | 'new'           // Just detected, not yet processed
  | 'triaged'       // Categorized and prioritized
  | 'in_progress'   // Currently being worked on
  | 'pending_approval'  // Awaiting human approval
  | 'blocked'       // Waiting on external dependency
  | 'completed'     // Fully resolved
  | 'failed';       // Processing failed

interface Attachment {
  filename: string;
  mime_type: string;
  size_bytes: number;
  path?: string;                 // Local path if stored
  url?: string;                  // External URL if cloud-stored
}
```

**State Transitions:**
```
new -> triaged -> in_progress -> completed
                -> blocked -> in_progress
                -> pending_approval -> in_progress (approved)
                -> failed
```

---

### 1.2 Invoice

Represents a financial document for billing clients, managed through Odoo.

```typescript
interface Invoice {
  // Identifiers
  id: string;                    // UUID v4
  odoo_id?: number;              // Odoo database ID (if synced)
  invoice_number: string;       // Human-readable invoice number (e.g., INV-2026-001)

  // Client Information
  client: {
    id: string;                  // Client identifier
    name: string;                // Legal business name
    email: string;               // Billing email
    phone?: string;
    address?: {
      street: string;
      city: string;
      state: string;
      postal_code: string;
      country: string;
    };
    vat_number?: string;         // Tax ID
  };

  // Financial Details
  currency: string;               // ISO 4217 currency code (e.g., "USD")
  subtotal: number;              // Sum of line items before tax
  tax_amount: number;            // Total tax
  total_amount: number;          // Final amount due
  amount_paid: number;           // Amount already paid
  amount_due: number;            // Remaining balance

  // Line Items
  line_items: InvoiceLineItem[];

  // Dates
  invoice_date: string;          // ISO 8601, when invoice was created
  due_date: string;              // ISO 8601, payment deadline
  sent_at?: string;              // ISO 8601, when sent to client
  paid_at?: string;              // ISO 8601, when fully paid

  // State
  status: InvoiceStatus;
  payment_status: PaymentStatus;
  approval_status: ApprovalStatus;

  // Odoo-specific
  odoo_journal_id?: number;      // Odoo journal reference
  odoo_attachment_id?: number;   // PDF attachment in Odoo

  // Metadata
  created_by: string;            // System or user who created
  notes?: string;                // Additional notes
  terms?: string;                // Payment terms
}

interface InvoiceLineItem {
  id: string;
  description: string;
  quantity: number;
  unit_price: number;
  unit: string;                  // e.g., "hours", "items", "units"
  tax_rate?: number;             // e.g., 0.20 for 20%
  subtotal: number;
  odoo_product_id?: number;      // Odoo product reference
}

type InvoiceStatus =
  | 'draft'          // Created, not yet sent
  | 'sent'           // Sent to client
  | 'viewed'         // Client viewed (if tracking enabled)
  | 'overdue'        // Past due date, unpaid
  | 'paid'           // Fully paid
  | 'cancelled'      // Cancelled void
  | 'void';          // Legally voided

type PaymentStatus =
  | 'unpaid'
  | 'partial'        // Partially paid
  | 'paid'
  | 'overdue';

type ApprovalStatus =
  | 'pending'        // Awaiting human approval
  | 'approved'      // Approved by human
  | 'rejected'      // Rejected by human
  | 'auto_approved'; // Below threshold, auto-approved
```

**State Transitions:**
```
draft -> sent -> viewed -> paid
              -> overdue -> paid
              -> cancelled/void
draft -> pending_approval -> approved -> sent
                        -> rejected -> draft
```

**Validation Rules:**
- `total_amount` must equal `subtotal + tax_amount`
- `amount_due` must equal `total_amount - amount_paid`
- `due_date` must be >= `invoice_date`
- At least one line item required
- Client email required for sending

---

### 1.3 Payment

Represents a financial transaction, either incoming (from client) or outgoing (to vendor).

```typescript
interface Payment {
  // Identifiers
  id: string;                    // UUID v4
  odoo_id?: number;              // Odoo database ID
  payment_reference: string;    // Human-readable reference (e.g., PAY-2026-001)

  // Transaction Details
  type: PaymentType;             // incoming or outgoing
  amount: number;
  currency: string;               // ISO 4217

  // Party Information
  counterparty: {
    id: string;
    name: string;
    type: 'customer' | 'vendor' | 'other';
    bank_account?: {
      bank_name: string;
      account_number: string;
      routing_number?: string;
      iban?: string;
      swift?: string;
    };
  };

  // Invoice Linkage
  linked_invoices?: {
    invoice_id: string;
    invoice_number: string;
    amount_applied: number;
  }[];

  // Dates
  payment_date: string;           // ISO 8601, when payment was made
  effective_date?: string;        // ISO 8601, when funds clear
  created_at: string;

  // State
  status: PaymentStatus;
  reconciliation_status: ReconciliationStatus;
  approval_status: ApprovalStatus;

  // External Reference
  external_reference?: string;    // Bank transaction ID
  external_account?: string;     // Source/destination account

  // Odoo-specific
  odoo_journal_id?: number;
  odoo_move_id?: number;

  // Metadata
  description?: string;
  category?: string;             // e.g., "invoice_payment", "refund", "fee"
  created_by: string;
}

type PaymentType = 'incoming' | 'outgoing' | 'transfer';
type PaymentStatus =
  | 'draft'          // Created, not yet processed
  | 'pending'        // Awaiting processing
  | 'processing'    // Being processed
  | 'completed'     // Successfully completed
  | 'failed'        // Failed
  | 'cancelled';    // Cancelled

type ReconciliationStatus =
  | 'unmatched'      // No invoice linked
  | 'matched'        // Linked to invoice
  | 'partial'        // Partial match to invoice
  | 'overmatched';   // Matched to more than needed
```

**State Transitions:**
```
draft -> pending -> processing -> completed
                           -> failed
draft -> pending_approval -> approved -> processing -> completed
                         -> rejected -> draft
```

**Validation Rules:**
- For incoming payments > $100: requires human approval
- For outgoing payments: always requires human approval
- For new payees: always requires human approval (FR-004)
- Must link to invoice for reconciliation

---

### 1.4 SocialPost

Represents content scheduled for publication on social media platforms.

```typescript
interface SocialPost {
  // Identifiers
  id: string;                    // UUID v4
  content_id?: string;           // Platform-specific post ID after publishing

  // Content
  content: {
    text: string;                // Main post text
    media?: {
      type: 'image' | 'video' | 'gif' | 'link';
      urls: string[];            // URLs to media assets
      captions?: string[];
    };
    link_preview?: {
      url: string;
      title?: string;
      description?: string;
      image_url?: string;
    };
  };

  // Platform Targeting
  platforms: SocialPlatform[];
  platform_specific?: {
    twitter?: {
      reply_to?: string;        // Tweet ID to reply to
      poll_options?: string[];   // Poll choices
    };
    linkedin?: {
      article_url?: string;
      visibility: 'public' | 'connections';
    };
    facebook?: {
      page_id?: string;
      targeting?: object;
    };
    instagram?: {
      story?: boolean;
      carousel?: string[];
    };
  };

  // Scheduling
  scheduled_at?: string;         // ISO 8601, when to publish
  published_at?: string;         // ISO 8601, actual publish time
  retry_count: number;           // Number of publish retries

  // State
  status: SocialPostStatus;
  approval_status: ApprovalStatus;

  // Engagement Metrics (populated after publishing)
  metrics?: {
    impressions?: number;
    reach?: number;
    engagements: number;
    likes: number;
    comments: number;
    shares: number;
    clicks?: number;
  };

  // Source
  source: {
    type: 'manual' | 'scheduled' | 'automated';
    trigger_event?: string;     // What triggered creation
    business_goals_ref?: string; // Reference to Business_Goals.md
  };

  // Metadata
  created_by: string;
  created_at: string;
  updated_at: string;
}

type SocialPlatform = 'twitter' | 'facebook' | 'instagram' | 'linkedin';
type SocialPostStatus =
  | 'draft'          // Created, not yet scheduled
  | 'scheduled'      // Scheduled for future publication
  | 'publishing'     // Currently being published
  | 'published'      // Successfully published
  | 'failed'         // Failed to publish
  | 'deleted';       // Deleted from platform
```

**State Transitions:**
```
draft -> scheduled -> publishing -> published
                              -> failed -> scheduled (retry)
draft -> pending_approval -> approved -> scheduled
                        -> rejected -> draft
```

**Validation Rules:**
- Text length: platform-specific (Twitter: 280 chars, others: more lenient)
- At least one platform required
- Scheduled time must be in the future
- Maximum 3 retries for publishing failures

---

### 1.5 BrandMention

Represents a social media mention of the brand that requires monitoring and potentially a response.

```typescript
interface BrandMention {
  // Identifiers
  id: string;                    // UUID v4
  platform_mention_id: string;   // Platform-specific mention ID

  // Source
  platform: SocialPlatform;
  post_url: string;              // Direct link to the post
  author: {
    handle: string;
    display_name: string;
    follower_count?: number;
    verified?: boolean;
  };

  // Content
  content: {
    text: string;
    media_urls?: string[];
    is_reply: boolean;
    is_mention: boolean;
    is_repost: boolean;
  };

  // Analysis
  sentiment: SentimentAnalysis;
  topics?: string[];             // Detected topics/themes
  intent?: 'inquiry' | 'compliment' | 'complaint' | 'feedback' | 'spam';

  // Response
  response_status: ResponseStatus;
  response_content?: {
    text: string;
    scheduled_at?: string;
    published_at?: string;
  };

  // Alerting
  alert_status: AlertStatus;
  alert_level?: 'info' | 'warning' | 'critical';
  alert_reason?: string;

  // Timestamps
  detected_at: string;            // When mention was detected
  analyzed_at?: string;          // When sentiment analysis ran
  responded_at?: string;          // When response was sent

  // Metadata
  priority: Priority;
  created_at: string;
}

type SentimentAnalysis = {
  score: number;                 // -1.0 to 1.0
  label: 'positive' | 'negative' | 'neutral';
  confidence: number;            // 0.0 to 1.0
  reasons?: string[];            // Why this sentiment was assigned
};

type ResponseStatus =
  | 'detected'       // New, not yet reviewed
  | 'analyzed'       // Sentiment analyzed
  | 'pending'        // Awaiting response decision
  | 'approved'       // Response approved
  | 'scheduled'      // Response scheduled
  | 'published'      // Response sent
  | 'ignored';       // No response needed

type AlertStatus =
  | 'none'           // No alert needed
  | 'sent'           // Alert sent to human
  | 'acknowledged'   // Human acknowledged
  | 'resolved';      // Issue resolved
```

**State Transitions:**
```
detected -> analyzed -> pending -> approved -> scheduled -> published
                                              -> ignored
                      -> ignored
```

**Validation Rules:**
- Negative sentiment with confidence > 0.7: triggers alert within 30 minutes (FR-006)
- Response to negative mentions requires human approval
- Alert level thresholds configurable per business

---

### 1.6 HealthStatus

Represents system component monitoring data for operational visibility.

```typescript
interface HealthStatus {
  // System Identity
  system_id: string;             // Unique system identifier
  system_name: string;
  version: string;

  // Overall Health
  overall_status: ComponentStatus;
  uptime_seconds: number;

  // Component Status
  components: ComponentHealth[];

  // Resource Usage
  resources: {
    cpu: {
      usage_percent: number;
      cores: number;
    };
    memory: {
      used_bytes: number;
      total_bytes: number;
      usage_percent: number;
    };
    disk: {
      used_bytes: number;
      total_bytes: number;
      usage_percent: number;
    };
    network?: {
      status: 'online' | 'offline';
      latency_ms?: number;
    };
  };

  // Watchers
  watchers: WatcherStatus[];

  // Errors
  recent_errors: ErrorRecord[];

  // Timestamps
  timestamp: string;             // ISO 8601
  last_restart?: string;         // ISO 8601
}

type ComponentStatus = 'healthy' | 'degraded' | 'unhealthy' | 'unknown';

interface ComponentHealth {
  name: string;                  // e.g., "email_watcher", "odoo_client"
  status: ComponentStatus;
  last_check: string;            // ISO 8601
  response_time_ms?: number;
  error_count_1h: number;
}

interface WatcherStatus {
  id: string;
  name: string;                  // e.g., "gmail_watcher", "filesystem_watcher"
  status: 'running' | 'stopped' | 'error';
  last_event_at?: string;
  items_processed_1h: number;
  error_count_1h: number;
}

interface ErrorRecord {
  id: string;
  timestamp: string;
  component: string;
  error_type: ErrorType;
  message: string;
  details?: object;
  resolved: boolean;
  resolved_at?: string;
}

type ErrorType =
  | 'transient'      // Network timeout, rate limit - retry with backoff
  | 'auth'           // Expired token - alert human, pause
  | 'logic'          // Claude misinterpretation - human review queue
  | 'data'           // Corrupted file - quarantine + alert
  | 'system';        // Process crash - watchdog + auto-restart
```

---

## 2. Entity Relationships

```
                    ┌─────────────────┐
                    │   ActionItem   │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌──────────────┐    ┌────────────────┐    ┌──────────────┐
│   Invoice    │    │   SocialPost   │    │BrandMention │
│  (1:1 or 1:N)│    │   (1:N)        │    │  (1:N)      │
└──────┬───────┘    └────────────────┘    └──────────────┘
       │
       │ (1:N)
       ▼
┌──────────────┐
│   Payment    │
└──────────────┘
```

### Relationship Cardinalities

| From | To | Type | Description |
|------|-----|------|-------------|
| ActionItem | Invoice | 1:1 or 0 | Invoice creation can be triggered by ActionItem |
| Invoice | Payment | 1:N | Multiple payments can be applied to one invoice |
| ActionItem | SocialPost | 1:N | One action can generate multiple posts |
| ActionItem | BrandMention | 1:1 | Brand mentions create action items |
| SocialPost | BrandMention | 1:N | Published posts can generate mentions |

---

## 3. State Machine Summary

### ActionItem State Machine
```
                    ┌─────────────┐
                    │    new     │
                    └──────┬──────┘
                           │ triage
                           ▼
                    ┌─────────────┐
              ┌────▶│  triaged    │◀────┐
              │     └──────┬──────┘     │
              │            │ process    │
              │            ▼            │
              │     ┌─────────────┐     │
              │     │in_progress  │     │
              │     └──────┬──────┘     │
              │            │            │
     approve  │            │ complete   │ reject
              │            ▼            │
              │     ┌─────────────┐     │
              │     │pending_     │     │
              │     │approval     │     │
              │     └──────┬──────┘     │
              │            │            │
              │      approve           │
              │            │            │
              └────────────┴────────────┘
```

### Invoice State Machine
```
┌─────────┐    send    ┌────────┐    view    ┌────────┐
│ draft   │───────────▶│ sent   │───────────▶│ viewed │
└─────────┘           └────────┘            └────┬─────┘
    ▲                                               │
    │                                               │ pay
    │                  ┌─────────┐                  │
    │ reject           │overdue  │◀──────────────────┘
    │                  └────┬────┘
    │                       │ pay
    │                       ▼
    │                  ┌─────────┐
    └──────────────────│  paid   │
                       └─────────┘
```

---

## 4. Data Validation Rules

### Financial Thresholds (from FR-004)
| Transaction Type | Threshold | Approval Required |
|-----------------|-----------|-------------------|
| Invoice creation | Any | Draft only, approval for sending |
| Payment (incoming) | > $100 | Approval required |
| Payment (outgoing) | Any | Always requires approval |
| New payee | Any | Always requires approval |

### Timing Requirements (from Success Criteria)
| Metric | Target | Threshold |
|--------|--------|-----------|
| Action item detection | < 5 min | 95% of items |
| Invoice generation | < 30 min | From service completion |
| Brand mention alert | < 30 min | Negative sentiment |
| Process restart | < 60 sec | After crash detection |

### Content Limits
| Entity | Field | Limit |
|--------|-------|-------|
| ActionItem | title | 200 characters |
| ActionItem | content | 50,000 characters |
| SocialPost | text (Twitter) | 280 characters |
| SocialPost | text (Facebook) | 63,206 characters |
| SocialPost | text (LinkedIn) | 3,000 characters |
| SocialPost | text (Instagram) | 2,200 characters |
| Invoice | line_items | Maximum 100 items |
| Payment | linked_invoices | Maximum 10 invoices |

---

## 5. JSON Schemas for API Contracts

### 5.1 ActionItem Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ActionItem",
  "type": "object",
  "required": ["id", "source_type", "source_identifier", "title", "content", "priority", "status", "created_at"],
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique identifier"
    },
    "source_type": {
      "type": "string",
      "enum": ["email", "whatsapp", "file_drop", "scheduled", "manual"],
      "description": "Origin of the item"
    },
    "source_identifier": {
      "type": "string",
      "minLength": 1,
      "description": "External source identifier"
    },
    "content_hash": {
      "type": "string",
      "pattern": "^[a-f0-9]{64}$",
      "description": "SHA-256 hash for deduplication"
    },
    "title": {
      "type": "string",
      "minLength": 1,
      "maxLength": 200,
      "description": "Brief summary"
    },
    "content": {
      "type": "string",
      "maxLength": 50000,
      "description": "Full content/body"
    },
    "priority": {
      "type": "string",
      "enum": ["urgent", "high", "medium", "low"],
      "default": "medium"
    },
    "status": {
      "type": "string",
      "enum": ["new", "triaged", "in_progress", "pending_approval", "blocked", "completed", "failed"],
      "default": "new"
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp"
    },
    "due_date": {
      "type": "string",
      "format": "date-time",
      "description": "Optional deadline"
    },
    "category": {
      "type": "string",
      "description": "Business category"
    },
    "tags": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Tags for filtering"
    },
    "metadata": {
      "type": "object",
      "properties": {
        "sender": { "type": "string" },
        "recipient": { "type": "string" },
        "subject": { "type": "string" },
        "attachments": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "filename": { "type": "string" },
              "mime_type": { "type": "string" },
              "size_bytes": { "type": "integer" }
            }
          }
        }
      }
    }
  }
}
```

### 5.2 Invoice Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Invoice",
  "type": "object",
  "required": ["id", "invoice_number", "client", "currency", "line_items", "invoice_date", "due_date", "status"],
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid"
    },
    "odoo_id": {
      "type": "integer",
      "description": "Odoo database ID"
    },
    "invoice_number": {
      "type": "string",
      "pattern": "^INV-\\d{4}-\\d{3}$",
      "description": "Human-readable invoice number"
    },
    "client": {
      "type": "object",
      "required": ["id", "name", "email"],
      "properties": {
        "id": { "type": "string" },
        "name": { "type": "string" },
        "email": { "type": "string", "format": "email" },
        "address": {
          "type": "object",
          "properties": {
            "street": { "type": "string" },
            "city": { "type": "string" },
            "state": { "type": "string" },
            "postal_code": { "type": "string" },
            "country": { "type": "string" }
          }
        }
      }
    },
    "currency": {
      "type": "string",
      "pattern": "^[A-Z]{3}$",
      "description": "ISO 4217 currency code"
    },
    "subtotal": {
      "type": "number",
      "minimum": 0,
      "description": "Sum of line items before tax"
    },
    "tax_amount": {
      "type": "number",
      "minimum": 0,
      "default": 0
    },
    "total_amount": {
      "type": "number",
      "minimum": 0
    },
    "amount_paid": {
      "type": "number",
      "minimum": 0,
      "default": 0
    },
    "amount_due": {
      "type": "number",
      "minimum": 0
    },
    "line_items": {
      "type": "array",
      "minItems": 1,
      "maxItems": 100,
      "items": {
        "type": "object",
        "required": ["id", "description", "quantity", "unit_price", "subtotal"],
        "properties": {
          "id": { "type": "string", "format": "uuid" },
          "description": { "type": "string" },
          "quantity": { "type": "number", "minimum": 0.01 },
          "unit_price": { "type": "number", "minimum": 0 },
          "unit": { "type": "string", "default": "units" },
          "tax_rate": { "type": "number", "minimum": 0, "maximum": 1 },
          "subtotal": { "type": "number", "minimum": 0 }
        }
      }
    },
    "invoice_date": {
      "type": "string",
      "format": "date"
    },
    "due_date": {
      "type": "string",
      "format": "date"
    },
    "status": {
      "type": "string",
      "enum": ["draft", "sent", "viewed", "overdue", "paid", "cancelled", "void"]
    },
    "approval_status": {
      "type": "string",
      "enum": ["pending", "approved", "rejected", "auto_approved"],
      "default": "pending"
    }
  }
}
```

### 5.3 Payment Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Payment",
  "type": "object",
  "required": ["id", "payment_reference", "type", "amount", "currency", "counterparty", "payment_date", "status"],
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid"
    },
    "payment_reference": {
      "type": "string",
      "pattern": "^PAY-\\d{4}-\\d{3}$"
    },
    "type": {
      "type": "string",
      "enum": ["incoming", "outgoing", "transfer"]
    },
    "amount": {
      "type": "number",
      "minimum": 0.01
    },
    "currency": {
      "type": "string",
      "pattern": "^[A-Z]{3}$"
    },
    "counterparty": {
      "type": "object",
      "required": ["id", "name", "type"],
      "properties": {
        "id": { "type": "string" },
        "name": { "type": "string" },
        "type": { "type": "string", "enum": ["customer", "vendor", "other"] },
        "bank_account": {
          "type": "object",
          "properties": {
            "bank_name": { "type": "string" },
            "account_number": { "type": "string" },
            "iban": { "type": "string" },
            "swift": { "type": "string" }
          }
        }
      }
    },
    "linked_invoices": {
      "type": "array",
      "maxItems": 10,
      "items": {
        "type": "object",
        "properties": {
          "invoice_id": { "type": "string", "format": "uuid" },
          "invoice_number": { "type": "string" },
          "amount_applied": { "type": "number", "minimum": 0 }
        }
      }
    },
    "payment_date": {
      "type": "string",
      "format": "date"
    },
    "status": {
      "type": "string",
      "enum": ["draft", "pending", "processing", "completed", "failed", "cancelled"]
    },
    "reconciliation_status": {
      "type": "string",
      "enum": ["unmatched", "matched", "partial", "overmatched"],
      "default": "unmatched"
    },
    "approval_status": {
      "type": "string",
      "enum": ["pending", "approved", "rejected", "auto_approved"],
      "default": "pending"
    }
  }
}
```

### 5.4 SocialPost Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SocialPost",
  "type": "object",
  "required": ["id", "content", "platforms", "status", "created_at"],
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid"
    },
    "content": {
      "type": "object",
      "required": ["text"],
      "properties": {
        "text": {
          "type": "string",
          "minLength": 1,
          "maxLength": 63206
        },
        "media": {
          "type": "object",
          "properties": {
            "type": { "type": "string", "enum": ["image", "video", "gif", "link"] },
            "urls": {
              "type": "array",
              "items": { "type": "string", "format": "uri" },
              "maxItems": 10
            }
          }
        }
      }
    },
    "platforms": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "string",
        "enum": ["twitter", "facebook", "instagram", "linkedin"]
      }
    },
    "scheduled_at": {
      "type": "string",
      "format": "date-time",
      "description": "Must be in the future for drafts"
    },
    "status": {
      "type": "string",
      "enum": ["draft", "scheduled", "publishing", "published", "failed", "deleted"]
    },
    "approval_status": {
      "type": "string",
      "enum": ["pending", "approved", "rejected", "auto_approved"],
      "default": "pending"
    },
    "metrics": {
      "type": "object",
      "properties": {
        "impressions": { "type": "integer", "minimum": 0 },
        "engagements": { "type": "integer", "minimum": 0 },
        "likes": { "type": "integer", "minimum": 0 },
        "comments": { "type": "integer", "minimum": 0 },
        "shares": { "type": "integer", "minimum": 0 }
      }
    },
    "retry_count": {
      "type": "integer",
      "minimum": 0,
      "maximum": 3,
      "default": 0
    }
  }
}
```

### 5.5 BrandMention Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "BrandMention",
  "type": "object",
  "required": ["id", "platform", "post_url", "author", "content", "sentiment", "response_status", "detected_at", "created_at"],
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid"
    },
    "platform": {
      "type": "string",
      "enum": ["twitter", "facebook", "instagram", "linkedin"]
    },
    "post_url": {
      "type": "string",
      "format": "uri"
    },
    "author": {
      "type": "object",
      "required": ["handle", "display_name"],
      "properties": {
        "handle": { "type": "string" },
        "display_name": { "type": "string" },
        "follower_count": { "type": "integer", "minimum": 0 },
        "verified": { "type": "boolean" }
      }
    },
    "content": {
      "type": "object",
      "required": ["text"],
      "properties": {
        "text": { "type": "string" },
        "media_urls": {
          "type": "array",
          "items": { "type": "string", "format": "uri" }
        },
        "is_reply": { "type": "boolean" },
        "is_mention": { "type": "boolean" },
        "is_repost": { "type": "boolean" }
      }
    },
    "sentiment": {
      "type": "object",
      "required": ["score", "label", "confidence"],
      "properties": {
        "score": { "type": "number", "minimum": -1, "maximum": 1 },
        "label": { "type": "string", "enum": ["positive", "negative", "neutral"] },
        "confidence": { "type": "number", "minimum": 0, "maximum": 1 }
      }
    },
    "response_status": {
      "type": "string",
      "enum": ["detected", "analyzed", "pending", "approved", "scheduled", "published", "ignored"]
    },
    "alert_status": {
      "type": "string",
      "enum": ["none", "sent", "acknowledged", "resolved"],
      "default": "none"
    },
    "alert_level": {
      "type": "string",
      "enum": ["info", "warning", "critical"]
    },
    "priority": {
      "type": "string",
      "enum": ["urgent", "high", "medium", "low"],
      "default": "medium"
    },
    "detected_at": {
      "type": "string",
      "format": "date-time"
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    }
  }
}
```

### 5.6 HealthStatus Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "HealthStatus",
  "type": "object",
  "required": ["system_id", "system_name", "overall_status", "components", "resources", "timestamp"],
  "properties": {
    "system_id": {
      "type": "string"
    },
    "system_name": {
      "type": "string"
    },
    "version": {
      "type": "string"
    },
    "overall_status": {
      "type": "string",
      "enum": ["healthy", "degraded", "unhealthy", "unknown"]
    },
    "uptime_seconds": {
      "type": "integer",
      "minimum": 0
    },
    "components": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "status", "last_check"],
        "properties": {
          "name": { "type": "string" },
          "status": { "type": "string", "enum": ["healthy", "degraded", "unhealthy", "unknown"] },
          "last_check": { "type": "string", "format": "date-time" },
          "response_time_ms": { "type": "integer" },
          "error_count_1h": { "type": "integer", "minimum": 0 }
        }
      }
    },
    "resources": {
      "type": "object",
      "required": ["cpu", "memory", "disk"],
      "properties": {
        "cpu": {
          "type": "object",
          "properties": {
            "usage_percent": { "type": "number", "minimum": 0, "maximum": 100 },
            "cores": { "type": "integer" }
          }
        },
        "memory": {
          "type": "object",
          "properties": {
            "used_bytes": { "type": "integer" },
            "total_bytes": { "type": "integer" },
            "usage_percent": { "type": "number", "minimum": 0, "maximum": 100 }
          }
        },
        "disk": {
          "type": "object",
          "properties": {
            "used_bytes": { "type": "integer" },
            "total_bytes": { "type": "integer" },
            "usage_percent": { "type": "number", "minimum": 0, "maximum": 100 }
          }
        }
      }
    },
    "watchers": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "string" },
          "name": { "type": "string" },
          "status": { "type": "string", "enum": ["running", "stopped", "error"] },
          "items_processed_1h": { "type": "integer" },
          "error_count_1h": { "type": "integer" }
        }
      }
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    }
  }
}
```

---

## 6. File Storage Conventions

For the file-based storage system, entities map to the following Obsidian vault structure:

```
/Vault/
├── Needs_Action/
│   └── action_items/
│       ├── ACTION_{uuid}.md    # ActionItem files
│       └── action_{timestamp}.md
├── Pending_Approval/
│   ├── invoices/
│   │   └── INV_{number}.md     # Invoice approval requests
│   ├── payments/
│   │   └── PAY_{number}.md     # Payment approval requests
│   └── social_posts/
│       └── POST_{platform}_{uuid}.md  # Post approval requests
├── Approved/
│   └── (approved items move here for execution)
├── Done/
│   └── (completed items)
├── Invoices/
│   └── {year}/
│       └── INV_{number}.md     # Final invoice records
├── Payments/
│   └── {year}/
│       └── PAY_{number}.md     # Final payment records
├── Social/
│   ├── scheduled/
│   ├── published/
│   └── mentions/
├── Dashboard/
│   └── Dashboard.md
├── Logs/
│   └── {YYYY-MM-DD}.json       # Audit logs
└── Health/
    └── health.json             # Current health status
```

---

## 7. Scale Considerations

For small business scale (1-10 employees, <100 transactions/month):

| Entity | Expected Volume | Storage |
|--------|-----------------|---------|
| ActionItem | ~500/month | ~2 MB |
| Invoice | ~50/month | ~500 KB |
| Payment | ~100/month | ~500 KB |
| SocialPost | ~12/month (1-3/platform/week) | ~100 KB |
| BrandMention | ~50/month | ~200 KB |
| HealthStatus | ~30,000/month (every 1 min) | ~5 MB |

**Data Retention:**
- Active data: Indefinite
- Audit logs: 2 years minimum (FR-010)
- Temporary files: 7 days (FR-013)
- Health history: 30 days rolling window

---

*Document Version: 1.0*
*Last Updated: 2026-02-21*
*Specification: 001-ai-employee*
