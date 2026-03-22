CREATE OR REPLACE FUNCTION update_activity_path()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.parent_id IS NULL THEN
        NEW.path = NEW.id::text::ltree;
    ELSE
        SELECT path || NEW.id::text INTO NEW.path
        FROM activities
        WHERE id = NEW.parent_id;

        IF NEW.path IS NULL THEN
            RAISE EXCEPTION 'Parent activity % not found', NEW.parent_id;
        END IF;
    END IF;

    IF nlevel(NEW.path) > 3 THEN
        RAISE EXCEPTION 'Max depth of 3 exceeded';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_activity_path
BEFORE INSERT OR UPDATE OF parent_id ON activities
FOR EACH ROW EXECUTE FUNCTION update_activity_path();

CREATE OR REPLACE FUNCTION cascade_update_activity_path()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE activities
    SET path = NEW.path || subpath(path, nlevel(OLD.path))
    WHERE path <@ OLD.path AND id != NEW.id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_cascade_update_activity_path
AFTER UPDATE OF parent_id ON activities
FOR EACH ROW EXECUTE FUNCTION cascade_update_activity_path();
