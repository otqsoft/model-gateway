// Supabase 客户端配置

import { createClient } from "@supabase/supabase-js";

const supabaseUrl = "https://ogffqjssnfosjassuyjj.supabase.co";
const supabaseKey =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9nZmZxanNzbmZvc2phc3N1eWpqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Mjc0MDE3MiwiZXhwIjoyMDg4MzE2MTcyfQ.zCx814BX93enG4HnspFndVcbaQsxX14csAIpJfMu868";

export const supabase = createClient(supabaseUrl, supabaseKey);
