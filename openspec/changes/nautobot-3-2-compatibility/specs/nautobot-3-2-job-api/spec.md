## ADDED Requirements

### Requirement: Job enqueue uses Nautobot 3.2 job_kwargs API

The system SHALL pass job keyword arguments to `JobResult.enqueue_job()` as a single
named `job_kwargs` parameter rather than using the deprecated `**kwargs` splat pattern.

#### Scenario: Enqueue job with job_kwargs parameter

- **WHEN** a user requests live data via the Device or Interface API endpoint
- **THEN** the `_enqueue_job()` method calls `JobResult.enqueue_job(job, user=user, task_queue=..., job_kwargs=job_kwargs)`
- **AND** the Nautobot 3.2 deprecation warning for `**job_kwargs` is NOT emitted
- **AND** the job is enqueued successfully with the same keyword arguments as before

#### Scenario: Backward compatible with Nautobot 3.0-3.1

- **WHEN** the app runs on a Nautobot version that supports `job_kwargs` as a named parameter
- **THEN** the `_enqueue_job()` method passes `job_kwargs` as a single dict value
- **AND** the job receives the same keyword arguments it received before the change
