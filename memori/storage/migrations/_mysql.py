r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""

migrations = {
    1: [
        {
            "description": "create table memori_schema_version",
            "operation": """
                create table if not exists memori_schema_version(
                    num bigint not null primary key
                )
            """,
        },
        {
            "description": "create table memori_entity",
            "operation": """
                create table if not exists memori_entity(
                    id bigint not null auto_increment,
                    uuid varchar(36) not null,
                    external_id varchar(100) not null,
                    date_created datetime not null default current_timestamp,
                    date_updated datetime default null on update current_timestamp,
                    --
                    primary key (id),
                    unique key (external_id),
                    unique key (uuid)
                )
            """,
        },
        {
            "description": "create table memori_process",
            "operation": """
                create table if not exists memori_process(
                    id bigint not null auto_increment,
                    uuid varchar(36) not null,
                    external_id varchar(100) not null,
                    date_created datetime not null default current_timestamp,
                    date_updated datetime default null on update current_timestamp,
                    --
                    primary key (id),
                    unique key (external_id),
                    unique key (uuid)
                )
            """,
        },
        {
            "description": "create table memori_session",
            "operation": """
                create table if not exists memori_session(
                    id bigint not null auto_increment,
                    uuid varchar(36) not null,
                    entity_id bigint default null,
                    process_id bigint default null,
                    date_created datetime not null default current_timestamp,
                    date_updated datetime default null on update current_timestamp,
                    --
                    primary key (id),
                    unique key (entity_id, id),
                    unique key (process_id, id),
                    unique key (uuid),
                    --
                    constraint fk_memori_sess_entity
                   foreign key (entity_id)
                    references memori_entity (id)
                     on delete cascade,
                    constraint fk_memori_sess_process
                   foreign key (process_id)
                    references memori_process (id)
                     on delete cascade
                )
            """,
        },
        {
            "description": "create table memori_conversation",
            "operation": """
                create table if not exists memori_conversation(
                    id bigint not null auto_increment,
                    uuid varchar(36) not null,
                    session_id bigint not null,
                    summary text default null,
                    date_created datetime not null default current_timestamp,
                    date_updated datetime default null on update current_timestamp,
                    --
                    primary key (id),
                    unique key (session_id),
                    unique key (uuid),
                    --
                    constraint fk_memori_conv_session
                   foreign key (session_id)
                    references memori_session (id)
                     on delete cascade
                )
            """,
        },
        {
            "description": "create table memori_conversation_message",
            "operation": """
                create table if not exists memori_conversation_message(
                    id bigint not null auto_increment,
                    uuid varchar(36) not null,
                    conversation_id bigint not null,
                    role varchar(255) not null,
                    type varchar(255) default null,
                    content text not null,
                    date_created datetime not null default current_timestamp,
                    date_updated datetime default null on update current_timestamp,
                    --
                    primary key (id),
                    unique key (conversation_id, id),
                    unique key (uuid),
                    --
                    constraint fk_memori_conv_msg_conv
                   foreign key (conversation_id)
                    references memori_conversation (id)
                     on delete cascade
                )
            """,
        },
        {
            "description": "create table memori_entity_fact",
            "operation": """
                create table if not exists memori_entity_fact(
                    id bigint not null auto_increment,
                    uuid varchar(36) not null,
                    entity_id bigint not null,
                    content text not null,
                    content_embedding blob not null,
                    num_times bigint not null,
                    date_last_time datetime not null,
                    uniq char(64) not null,
                    date_created datetime not null default current_timestamp,
                    date_updated datetime default null on update current_timestamp,
                    --
                    primary key (id),
                    unique key (entity_id, id),
                    unique key (entity_id, uniq),
                    unique key (uuid),
                    --
                    key idx_memori_entity_fact_entity_id_freq (entity_id, num_times desc, date_last_time desc),
                    --
                    constraint fk_memori_ent_summ_entity
                   foreign key (entity_id)
                    references memori_entity (id)
                     on delete cascade
                )
            """,
        },
        {
            "description": "create table memori_process_attribute",
            "operation": """
                create table if not exists memori_process_attribute(
                    id bigint not null auto_increment,
                    uuid varchar(36) not null,
                    process_id bigint not null,
                    content text not null,
                    num_times bigint not null,
                    date_last_time datetime not null,
                    uniq char(64) not null,
                    date_created datetime not null default current_timestamp,
                    date_updated datetime default null on update current_timestamp,
                    primary key (id),
                    unique key (process_id, id),
                    unique key (process_id, uniq),
                    unique key (uuid),
                    constraint fk_memori_proc_attribute
                   foreign key (process_id)
                    references memori_process (id)
                     on delete cascade
                )
            """,
        },
        {
            "description": "create table memori_subject",
            "operation": """
                create table if not exists memori_subject(
                    id bigint not null auto_increment,
                    uuid varchar(36) not null,
                    name varchar(255) not null,
                    type varchar(255) not null,
                    uniq char(64) not null,
                    date_created datetime not null default current_timestamp,
                    date_updated datetime default null on update current_timestamp,
                    --
                    primary key (id),
                    unique key (uniq),
                    unique key (uuid)
                )
            """,
        },
        {
            "description": "create table memori_predicate",
            "operation": """
                create table if not exists memori_predicate(
                    id bigint not null auto_increment,
                    uuid varchar(36) not null,
                    content text not null,
                    uniq char(64) not null,
                    date_created datetime not null default current_timestamp,
                    date_updated datetime default null on update current_timestamp,
                    --
                    primary key (id),
                    unique key (uniq),
                    unique key (uuid)
                )
            """,
        },
        {
            "description": "create table memori_object",
            "operation": """
                create table if not exists memori_object(
                    id bigint not null auto_increment,
                    uuid varchar(36) not null,
                    name varchar(255) not null,
                    type varchar(255) not null,
                    uniq char(64) not null,
                    date_created datetime not null default current_timestamp,
                    date_updated datetime default null on update current_timestamp,
                    --
                    primary key (id),
                    unique key (uniq),
                    unique key (uuid)
                )
            """,
        },
        {
            "description": "create table memori_knowledge_graph",
            "operation": """
                create table if not exists memori_knowledge_graph(
                    id bigint not null auto_increment,
                    uuid varchar(36) not null,
                    entity_id bigint not null,
                    subject_id bigint not null,
                    predicate_id bigint not null,
                    object_id bigint not null,
                    num_times bigint not null,
                    date_last_time datetime not null,
                    date_created datetime not null default current_timestamp,
                    date_updated datetime default null on update current_timestamp,
                    --
                    primary key (id),
                    unique key (entity_id, id),
                    unique key (entity_id, subject_id, predicate_id, object_id),
                    unique key (object_id, id),
                    unique key (predicate_id, id),
                    unique key (subject_id, id),
                    unique key (uuid),
                    --
                    constraint fk_memori_know_graph_entity
                       foreign key (entity_id)
                    references memori_entity (id)
                     on delete cascade,
                    --
                    constraint fk_memori_know_graph_object
                       foreign key (object_id)
                    references memori_object (id)
                     on delete cascade,
                    --
                    constraint fk_memori_know_graph_predicate
                       foreign key (predicate_id)
                    references memori_predicate (id)
                     on delete cascade,
                    --
                    constraint fk_memori_know_graph_subject
                       foreign key (subject_id)
                    references memori_subject (id)
                     on delete cascade
                )
            """,
        },
    ]
}
