rspamd_config.MAIL_AUTH = {
	callback = function(task)
		local uname = task:get_user()
		if uname then
			return 1
		end
	end
}

local monitoring_hosts = rspamd_config:add_map{
  url = "/etc/rspamd/custom/monitoring_nolog.map",
  description = "Monitoring hosts",
  type = "regexp"
}

rspamd_config:register_symbol({
  name = 'SMTP_ACCESS',
  type = 'postfilter',
  callback = function(task)
    local util = require("rspamd_util")
    local rspamd_logger = require "rspamd_logger"
    local rspamd_ip = require 'rspamd_ip'
    local uname = task:get_user()
    local limited_access = task:get_symbol("SMTP_LIMITED_ACCESS")

    if not uname then
      return false
    end

    if not limited_access then
      return false
    end

    local hash_key = 'SMTP_ALLOW_NETS_' .. uname

    local redis_params = rspamd_parse_redis_server('smtp_access')
    local ip = task:get_from_ip()

    if ip == nil or not ip:is_valid() then
      return false
    end

    local from_ip_string = tostring(ip)
    smtp_access_table = {from_ip_string}

    local maxbits = 128
    local minbits = 32
    if ip:get_version() == 4 then
        maxbits = 32
        minbits = 8
    end
    for i=maxbits,minbits,-1 do
      local nip = ip:apply_mask(i):to_string() .. "/" .. i
      table.insert(smtp_access_table, nip)
    end
    local function smtp_access_cb(err, data)
      if err then
        rspamd_logger.infox(rspamd_config, "smtp_access query request for ip %s returned invalid or empty data (\"%s\") or error (\"%s\")", ip, data, err)
        return false
      else
        rspamd_logger.infox(rspamd_config, "checking ip %s for smtp_access in %s", from_ip_string, hash_key)
        for k,v in pairs(data) do
          if (v and v ~= userdata and v == '1') then
            rspamd_logger.infox(rspamd_config, "found ip in smtp_access map")
            task:insert_result(true, 'SMTP_ACCESS', 0.0, from_ip_string)
            return true
          end
        end
        rspamd_logger.infox(rspamd_config, "couldnt find ip in smtp_access map")
        task:insert_result(true, 'SMTP_ACCESS', 999.0, from_ip_string)
        return true
      end
    end
    table.insert(smtp_access_table, 1, hash_key)
    local redis_ret_user = rspamd_redis_make_request(task,
      redis_params, -- connect params
      hash_key, -- hash key
      false, -- is write
      smtp_access_cb, --callback
      'HMGET', -- command
      smtp_access_table -- arguments
    )
    if not redis_ret_user then
      rspamd_logger.infox(rspamd_config, "cannot check smtp_access redis map")
    end
  end,
  priority = 10
})

rspamd_config:register_symbol({
  name = 'POSTMASTER_HANDLER',
  type = 'prefilter',
  callback = function(task)
  local rcpts = task:get_recipients('smtp')
  local rspamd_logger = require "rspamd_logger"
  local lua_util = require "lua_util"
  local from = task:get_from(1)

  -- not applying to mails with more than one rcpt to avoid bypassing filters by addressing postmaster
  if rcpts and #rcpts == 1 then
    for _,rcpt in ipairs(rcpts) do
      local rcpt_split = rspamd_str_split(rcpt['addr'], '@')
      if #rcpt_split == 2 then
        if rcpt_split[1] == 'postmaster' then
          task:set_pre_result('accept', 'whitelisting postmaster smtp rcpt', 'postmaster')
          return
        end
      end
    end
  end

  if from then
    for _,fr in ipairs(from) do
      local fr_split = rspamd_str_split(fr['addr'], '@')
      if #fr_split == 2 then
        if fr_split[1] == 'postmaster' and task:get_user() then
          -- no whitelist, keep signatures
          task:insert_result(true, 'POSTMASTER_FROM', -2500.0)
          return
        end
      end
    end
  end

  end,
  priority = 10
})

rspamd_config:register_symbol({
  name = 'KEEP_SPAM',
  type = 'prefilter',
  callback = function(task)
    local util = require("rspamd_util")
    local rspamd_logger = require "rspamd_logger"
    local rspamd_ip = require 'rspamd_ip'
    local uname = task:get_user()

    if uname then
      return false
    end

    local redis_params = rspamd_parse_redis_server('keep_spam')
    local ip = task:get_from_ip()

    if ip == nil or not ip:is_valid() then
      return false
    end

    local from_ip_string = tostring(ip)
    ip_check_table = {from_ip_string}

    local maxbits = 128
    local minbits = 32
    if ip:get_version() == 4 then
        maxbits = 32
        minbits = 8
    end
    for i=maxbits,minbits,-1 do
      local nip = ip:apply_mask(i):to_string() .. "/" .. i
      table.insert(ip_check_table, nip)
    end
    local function keep_spam_cb(err, data)
      if err then
        rspamd_logger.infox(rspamd_config, "keep_spam query request for ip %s returned invalid or empty data (\"%s\") or error (\"%s\")", ip, data, err)
        return false
      else
        for k,v in pairs(data) do
          if (v and v ~= userdata and v == '1') then
            rspamd_logger.infox(rspamd_config, "found ip in keep_spam map, setting pre-result")
            task:set_pre_result('accept', 'ip matched with forward hosts', 'keep_spam')
          end
        end
      end
    end
    table.insert(ip_check_table, 1, 'KEEP_SPAM')
    local redis_ret_user = rspamd_redis_make_request(task,
      redis_params, -- connect params
      'KEEP_SPAM', -- hash key
      false, -- is write
      keep_spam_cb, --callback
      'HMGET', -- command
      ip_check_table -- arguments
    )
    if not redis_ret_user then
      rspamd_logger.infox(rspamd_config, "cannot check keep_spam redis map")
    end
  end,
  priority = 19
})

rspamd_config:register_symbol({
  name = 'TLS_HEADER',
  type = 'postfilter',
  callback = function(task)
    local rspamd_logger = require "rspamd_logger"
    local tls_tag = task:get_request_header('TLS-Version')
    if type(tls_tag) == 'nil' then
      task:set_milter_reply({
        add_headers = {['X-Last-TLS-Session-Version'] = 'None'}
      })
    else
      task:set_milter_reply({
        add_headers = {['X-Last-TLS-Session-Version'] = tostring(tls_tag)}
      })
    end
  end,
  priority = 12
})

rspamd_config:register_symbol({
  name = 'DYN_RL_CHECK',
  type = 'prefilter',
  callback = function(task)
    local util = require("rspamd_util")
    local redis_params = rspamd_parse_redis_server('dyn_rl')
    local rspamd_logger = require "rspamd_logger"
    local envfrom = task:get_from(1)
    local envrcpt = task:get_recipients(1) or {}
    local uname = task:get_user()
    if not envfrom or not uname then
      return false
    end

    local uname = uname:lower()

    if #envrcpt == 1 and envrcpt[1].addr:lower() == uname then
      return false
    end

    local env_from_domain = envfrom[1].domain:lower() -- get smtp from domain in lower case

    local function redis_cb_user(err, data)

      if err or type(data) ~= 'string' then
        rspamd_logger.infox(rspamd_config, "dynamic ratelimit request for user %s returned invalid or empty data (\"%s\") or error (\"%s\") - trying dynamic ratelimit for domain...", uname, data, err)

        local function redis_key_cb_domain(err, data)
          if err or type(data) ~= 'string' then
            rspamd_logger.infox(rspamd_config, "dynamic ratelimit request for domain %s returned invalid or empty data (\"%s\") or error (\"%s\")", env_from_domain, data, err)
          else
            rspamd_logger.infox(rspamd_config, "found dynamic ratelimit in redis for domain %s with value %s", env_from_domain, data)
            task:insert_result('DYN_RL', 0.0, data, env_from_domain)
          end
        end

        local redis_ret_domain = rspamd_redis_make_request(task,
          redis_params, -- connect params
          env_from_domain, -- hash key
          false, -- is write
          redis_key_cb_domain, --callback
          'HGET', -- command
          {'RL_VALUE', env_from_domain} -- arguments
        )
        if not redis_ret_domain then
          rspamd_logger.infox(rspamd_config, "cannot make request to load ratelimit for domain")
        end
      else
        rspamd_logger.infox(rspamd_config, "found dynamic ratelimit in redis for user %s with value %s", uname, data)
        task:insert_result('DYN_RL', 0.0, data, uname)
      end

    end

    local redis_ret_user = rspamd_redis_make_request(task,
      redis_params, -- connect params
      uname, -- hash key
      false, -- is write
      redis_cb_user, --callback
      'HGET', -- command
      {'RL_VALUE', uname} -- arguments
    )
    if not redis_ret_user then
      rspamd_logger.infox(rspamd_config, "cannot make request to load ratelimit for user")
    end
    return true
  end,
  flags = 'empty',
  priority = 20
})

rspamd_config:register_symbol({
  name = 'NO_LOG_STAT',
  type = 'postfilter',
  callback = function(task)
    local from = task:get_header('From')
    if from and (monitoring_hosts:get_key(from) or from == "monit@localhost") then
      task:set_flag('no_log')
      task:set_flag('no_stat')
    end
  end
})
