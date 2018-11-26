-- Function: public.line_of_sight(geometry[])

-- DROP FUNCTION public.line_of_sight(geometry[]);

CREATE OR REPLACE FUNCTION public.line_of_sight(profile double precision[][])
  RETURNS boolean AS
$BODY$

DECLARE profile_len INTEGER;
DECLARE start_elevation DOUBLE PRECISION;
DECLARE end_elevation DOUBLE PRECISION;
DECLARE tot_distance DOUBLE PRECISION;
DECLARE end_pitch DOUBLE PRECISION;
DECLARE cur_pitch DOUBLE PRECISION;
DECLARE p DOUBLE PRECISION[];

BEGIN
	profile_len := array_length(profile, 1);
	start_elevation := profile[1][2] + 3;
	end_elevation := profile[profile_len][2] + 3;
	tot_distance := profile[profile_len][1];
	end_pitch := degrees(atan((end_elevation - start_elevation) / tot_distance)) - (tot_distance / (6370986 * pi() * 2) * 360);
	--RAISE 'start elev %, end elevation % tot_distance % end_pitch %',start_elevation, end_elevation,tot_distance,end_pitch;
	FOREACH p SLICE 1 IN ARRAY profile
	LOOP	
		cur_pitch := degrees(atan((p[2] - start_elevation) / p[1])) -	(p[1] / (6370986 * pi() * 2) * 360);
		IF cur_pitch >= end_pitch THEN
			--RAISE 'current elev: %, current distance: %, current pitch %, target pitch %',p[2], p[1], cur_pitch, end_pitch; 
			-- RAISE 'Cannot see over object at pitch %. Pitch to destination is %, start elevation %, object elevation = %, distination elevation = %, dist from start = %, dist from end = %',
                        --cur_pitch, end_pitch, start_elevation, p[2], end_elevation, p[1], tot_distance - p[1];
			RETURN FALSE;
		END IF;
		
	END LOOP;
	RETURN TRUE;
END;
$BODY$
  LANGUAGE plpgsql STABLE
  COST 1000;
ALTER FUNCTION public.line_of_sight(geometry[])
  OWNER TO gabriel;
