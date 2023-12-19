create table if not exists active_user_threads
(
    userid bigint not null,
    channel_id bigint,
    creation_date timestamp,
    primary key (userid)
);
