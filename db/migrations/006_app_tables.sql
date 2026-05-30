-- migrate:up

-- Web-written tables. Kept in `app` so they never touch the read-only `core` surface.

CREATE TABLE app.users (
  id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  email               text UNIQUE NOT NULL,
  auth_provider       text,
  subscription_status text CHECK (subscription_status IN ('active','inactive','trialing','past_due')),
  subscription_source text,                              -- stripe id, nullable
  created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE app.watchlists (
  user_id    bigint NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
  agency_id  bigint NOT NULL REFERENCES core.agencies(id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, agency_id)
);

-- "Request this agency" — pulls long-tail demand. Anonymous writes (no login).
CREATE TABLE app.agency_requests (
  id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  agency_id      bigint REFERENCES core.agencies(id) ON DELETE SET NULL,  -- may be an agency not yet listed
  requested_name text,
  email          text,
  created_at     timestamptz NOT NULL DEFAULT now()
);

-- Gate-funnel instrumentation. Anonymous writes.
CREATE TABLE app.conversion_events (
  id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  event_type text NOT NULL CHECK (event_type IN ('wall_hit','gate_view','checkout_start','paid')),
  agency_id  bigint REFERENCES core.agencies(id) ON DELETE SET NULL,      -- the triggering page
  user_id    bigint REFERENCES app.users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- migrate:down

DROP TABLE IF EXISTS app.conversion_events;
DROP TABLE IF EXISTS app.agency_requests;
DROP TABLE IF EXISTS app.watchlists;
DROP TABLE IF EXISTS app.users;
