static float xlua_pre_timer_master_cb(
                                   float                inElapsedSinceLastCall,
                                   float                inElapsedTimeSinceLastFlightLoop,
                                   int                  inCounter,
                                   void *               inRefcon)
{
	xlua_do_timers_for_time(xlua_get_simulated_time());

	if(XPLMGetDatai(g_replay_active) == 0)
	if(XPLMGetDataf(g_sim_period) > 0.0f)
	for(vector<module *>::iterator m = g_modules.begin(); m != g_modules.end(); ++m)
	{
		if((*m)->has_pre_physics())
			(*m)->pre_physics();
	}
	return -1;
}

static float xlua_post_timer_master_cb(
                                   float                inElapsedSinceLastCall,
                                   float                inElapsedTimeSinceLastFlightLoop,
                                   int                  inCounter,
                                   void *               inRefcon)
{
	if(XPLMGetDatai(g_replay_active) == 0)
	{
		if(XPLMGetDataf(g_sim_period) > 0.0f)
		for(vector<module *>::iterator m = g_modules.begin(); m != g_modules.end(); ++m)
		{
			if((*m)->has_post_physics())
				(*m)->post_physics();
		}
	}
	else
	for(vector<module *>::iterator m = g_modules.begin(); m != g_modules.end(); ++m)
	{
		if((*m)->has_post_replay())
			(*m)->post_replay();
	}
	return -1;
}
