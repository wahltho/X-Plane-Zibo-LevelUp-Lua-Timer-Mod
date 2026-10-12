static float xlua_pre_timer_master_cb(
                                   float                inElapsedSinceLastCall,
                                   float                inElapsedTimeSinceLastFlightLoop,
                                   int                  inCounter,
                                   void *               inRefcon)
{
	xlua_do_timers_for_time(xlua_get_simulated_time());

	if (XPLMGetDatai(g_replay_active) == 0 && XPLMGetDataf(g_sim_period) > 0.0f)
	{
		for (vector<module *>::iterator m = g_modules.begin(); m != g_modules.end(); ++m)
		{
			if ((*m)->has_pre_physics())
				(*m)->pre_physics();
		}
	}
	return -1;
}

static float xlua_post_timer_master_cb(
                                   float                inElapsedSinceLastCall,
                                   float                inElapsedTimeSinceLastFlightLoop,
                                   int                  inCounter,
                                   void *               inRefcon)
{
	bool const isInReplay = (XPLMGetDatai(g_replay_active) != 0);
	float const framePeriod = XPLMGetDataf(g_sim_period);
	for (auto &m : g_modules)
	{
		if (isInReplay)
		{
			if (m->has_post_replay())
				m->post_replay();
		}
		else if (framePeriod > 0.f)
		{
			if (m->has_post_physics())
				m->post_physics();
		}
	}

#if !MOBILE
	// XPLM has no close-callback API; clicking the X just toggles visibility.
	// Detect that here and tear the window + ImGui context down.
	if (profilerWnd && !XPLMGetWindowIsVisible(profilerWnd.get()))
	{
		profilerWnd.reset();          // XPLMDestroyWindow — no further callbacks
		profilerImguiCtx.reset();
	}
#endif
	return -1;
}
