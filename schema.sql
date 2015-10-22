BEGIN;
SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: encode_formats_id_seq1; Type: SEQUENCE; Schema: public
--

CREATE SEQUENCE encode_formats_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: encode_formats; Type: TABLE; Schema: public; Tablespace: 
--

CREATE TABLE encode_formats (
    id integer DEFAULT nextval('encode_formats_id_seq'::regclass) NOT NULL,
    format_name text NOT NULL,
    container text NOT NULL,
    video_bitrate integer NOT NULL,
    video_bitrate_tolerance integer NOT NULL,
    video_codec text NOT NULL,
    video_resolution text NOT NULL,
    audio_bitrate integer NOT NULL,
    audio_samplerate integer NOT NULL,
    audio_codec text NOT NULL,
    vpre_string text,
    aspect_ratio text NOT NULL,
    args_beginning text,
    args_video text,
    args_audio text,
    args_end text,
    apply_mp4box boolean DEFAULT false NOT NULL,
    file_extension character varying(5) DEFAULT 'mp4'::character varying NOT NULL,
    preset_string character varying DEFAULT '-preset slow'::character varying,
    normalise_level integer,
    ef_priority integer NOT NULL,
    pass integer DEFAULT 2
);

--
-- Name: TABLE encode_formats; Type: COMMENT; Schema: public
--

COMMENT ON TABLE encode_formats IS 'Stores ffmpeg options for the Encode Formats for EncodeSrv';


--
-- Name: COLUMN encode_formats.format_name; Type: COMMENT; Schema: public
--

COMMENT ON COLUMN encode_formats.format_name IS 'Name of the format (e.g. ipod)';


--
-- Name: COLUMN encode_formats.container; Type: COMMENT; Schema: public
--

COMMENT ON COLUMN encode_formats.container IS 'name of the container (e.g. mp4)';


--
-- Name: COLUMN encode_formats.video_bitrate; Type: COMMENT; Schema: public
--

COMMENT ON COLUMN encode_formats.video_bitrate IS 'video bitrate (in b/sec)';


--
-- Name: COLUMN encode_formats.video_bitrate_tolerance; Type: COMMENT; Schema: public
--

COMMENT ON COLUMN encode_formats.video_bitrate_tolerance IS 'video bitrate tolerance (in b/sec)';


--
-- Name: COLUMN encode_formats.video_codec; Type: COMMENT; Schema: public
--

COMMENT ON COLUMN encode_formats.video_codec IS 'video codec (e.g. libx264)';


--
-- Name: COLUMN encode_formats.video_resolution; Type: COMMENT; Schema: public
--

COMMENT ON COLUMN encode_formats.video_resolution IS 'Video resolution (e.g. 320x180)';


--
-- Name: COLUMN encode_formats.audio_bitrate; Type: COMMENT; Schema: public
--

COMMENT ON COLUMN encode_formats.audio_bitrate IS 'audio bitrate (in b/sec)';


--
-- Name: COLUMN encode_formats.audio_samplerate; Type: COMMENT; Schema: public
--

COMMENT ON COLUMN encode_formats.audio_samplerate IS 'audio samplerate (in Hz)';


--
-- Name: COLUMN encode_formats.audio_codec; Type: COMMENT; Schema: public
--

COMMENT ON COLUMN encode_formats.audio_codec IS 'audio codec (e.g libfaac)';


--
-- Name: COLUMN encode_formats.vpre_string; Type: COMMENT; Schema: public
--

COMMENT ON COLUMN encode_formats.vpre_string IS 'optional list of -vpre args (e.g. -vpre hq -vpre normal -vpre ipod320)';


--
-- Name: COLUMN encode_formats.aspect_ratio; Type: COMMENT; Schema: public
--

COMMENT ON COLUMN encode_formats.aspect_ratio IS 'aspect ratio (e.g. 16:9)';


--
-- Name: COLUMN encode_formats.args_beginning; Type: COMMENT; Schema: public
--

COMMENT ON COLUMN encode_formats.args_beginning IS 'optional extra args to put at beginning of command';


--
-- Name: COLUMN encode_formats.args_video; Type: COMMENT; Schema: public
--

COMMENT ON COLUMN encode_formats.args_video IS 'optional extra args to put after video options';


--
-- Name: COLUMN encode_formats.args_audio; Type: COMMENT; Schema: public
--

COMMENT ON COLUMN encode_formats.args_audio IS 'optional extra args to put after audio options';


--
-- Name: COLUMN encode_formats.args_end; Type: COMMENT; Schema: public
--

COMMENT ON COLUMN encode_formats.args_end IS 'optional extra args to put at the end';


--
-- Name: COLUMN encode_formats.apply_mp4box; Type: COMMENT; Schema: public
--

COMMENT ON COLUMN encode_formats.apply_mp4box IS 'Indicates whether the output file should be run through MP4Box. Note this should only be applied to MP4 formats.';


--
-- Name: COLUMN encode_formats.file_extension; Type: COMMENT; Schema: public
--

COMMENT ON COLUMN encode_formats.file_extension IS 'Extension of the resulting file. (e.g. mp4, avi, mov etc). Note this can be different from the container value';


--
-- Name: COLUMN encode_formats.ef_priority; Type: COMMENT; Schema: public
--

COMMENT ON COLUMN encode_formats.ef_priority IS 'Default priority for this format';


--
-- Name: COLUMN encode_formats.pass; Type: COMMENT; Schema: public
--

COMMENT ON COLUMN encode_formats.pass IS 'Whether the format is 1 or 2 pass';

--
-- Name: encode_formats_id_seq; Type: SEQUENCE OWNED BY; Schema: public
--

ALTER SEQUENCE encode_formats_id_seq OWNED BY encode_formats.id;


--
-- Name: encode_formats_pkey; Type: CONSTRAINT; Schema: public; Tablespace: 
--

ALTER TABLE ONLY encode_formats
    ADD CONSTRAINT encode_formats_pkey PRIMARY KEY (id);

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: encode_jobs_id_seq; Type: SEQUENCE; Schema: public
--

CREATE SEQUENCE encode_jobs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: encode_jobs; Type: TABLE; Schema: public; Tablespace: 
--

CREATE TABLE encode_jobs (
    id integer DEFAULT nextval('encode_jobs_id_seq'::regclass) NOT NULL,
    source_file text NOT NULL,
    destination_file text NOT NULL,
    format_id integer NOT NULL,
    status character varying(64) NOT NULL,
    video_id integer,
    working_directory text,
    user_id integer,
    priority numeric DEFAULT 5 NOT NULL
);

--
-- Name: TABLE encode_jobs; Type: COMMENT; Schema: public
--

COMMENT ON TABLE encode_jobs IS 'Stores the Encode Jobs for EncodeSrv';


--
-- Name: COLUMN encode_jobs.source_file; Type: COMMENT; Schema: public
--

COMMENT ON COLUMN encode_jobs.source_file IS 'Path to source file (e.g. /mnt/UserData/Shows/ManMan/Ep1/10_Man-Man-episode1_sum06.avi)';


--
-- Name: COLUMN encode_jobs.destination_file; Type: COMMENT; Schema: public
--

COMMENT ON COLUMN encode_jobs.destination_file IS 'Path to destination file (e.g. /mnt/videos/web/ipod/10_Man-Man-episode1_sum06.mp4) ';


--
-- Name: COLUMN encode_jobs.format_id; Type: COMMENT; Schema: public
--

COMMENT ON COLUMN encode_jobs.format_id IS 'ID to identify format type';


--
-- Name: COLUMN encode_jobs.status; Type: COMMENT; Schema: public
--

COMMENT ON COLUMN encode_jobs.status IS 'Indicates progress of the encode job. ';


--
-- Name: COLUMN encode_jobs.video_id; Type: COMMENT; Schema: public
--

COMMENT ON COLUMN encode_jobs.video_id IS 'ID of the relevant video_id. These entires are filled in before the video actaully exists. ';


--
-- Name: COLUMN encode_jobs.working_directory; Type: COMMENT; Schema: public
--

COMMENT ON COLUMN encode_jobs.working_directory IS 'Stores the working directory once a job has started';


--
-- Name: COLUMN encode_jobs.user_id; Type: COMMENT; Schema: public
--

COMMENT ON COLUMN encode_jobs.user_id IS 'ID of the user that requested the job';


--
-- Name: COLUMN encode_jobs.priority; Type: COMMENT; Schema: public
--

COMMENT ON COLUMN encode_jobs.priority IS 'Mainly for batch encode jobs like re-encodes. Could be used for giving certain events higher priority. Defaults to 5. Higher numbers = higher priority';


--
-- Name: encode_jobs_pkey; Type: CONSTRAINT; Schema: public; Tablespace: 
--

ALTER TABLE ONLY encode_jobs
    ADD CONSTRAINT encode_jobs_pkey PRIMARY KEY (id);

--
-- Name: encode_jobs_id_seq; Type: SEQUENCE OWNED BY; Schema: public
--

ALTER SEQUENCE encode_jobs_id_seq OWNED BY encode_jobs.id;

--
-- Name: encode_jobs_format_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: robert
--

ALTER TABLE ONLY encode_jobs
    ADD CONSTRAINT encode_jobs_format_id_fkey FOREIGN KEY (format_id) REFERENCES encode_formats(id) ON UPDATE CASCADE;



COMMIT;
