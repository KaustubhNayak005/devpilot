"""Neovim module — installs Neovim, ripgrep, fd-find, deploys lazy.nvim config."""

import logging
from pathlib import Path

from devpilot.modules.base import BaseModule, CheckResult
from devpilot.utils.shell import apt_install, run_command, which

logger = logging.getLogger("devpilot")

NVIM_CONFIG_DIR = Path.home() / ".config" / "nvim"
INIT_LUA_PATH = NVIM_CONFIG_DIR / "init.lua"

INIT_LUA_CONTENT = r"""-- DevPilot Neovim configuration
-- Bootstrapped by devpilot setup nvim

local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.loop.fs_stat(lazypath) then
  vim.fn.system({
    "git",
    "clone",
    "--filter=blob:none",
    "https://github.com/folke/lazy.nvim.git",
    "--branch=stable",
    lazypath,
  })
end
vim.opt.rtp:prepend(lazypath)

require("lazy").setup({
  {
    "nvim-telescope/telescope.nvim",
    tag = "0.1.8",
    dependencies = { "nvim-lua/plenary.nvim" },
    config = function()
      require("telescope").setup({
        defaults = {
          mappings = {
            i = {
              ["<C-u>"] = false,
              ["<C-d>"] = false,
            },
          },
        },
      })
    end,
  },
  {
    "nvim-treesitter/nvim-treesitter",
    build = ":TSUpdate",
    config = function()
      require("nvim-treesitter.configs").setup({
        ensure_installed = {
          "python", "javascript", "typescript", "lua", "vim", "vimdoc",
          "c", "cpp", "json", "yaml", "toml", "bash", "markdown",
        },
        auto_install = true,
        highlight = { enable = true },
        indent = { enable = true },
      })
    end,
  },
  {
    "williamboman/mason.nvim",
    build = ":MasonUpdate",
    config = function()
      require("mason").setup()
    end,
  },
  {
    "williamboman/mason-lspconfig.nvim",
    config = function()
      require("mason-lspconfig").setup({
        ensure_installed = {
          "lua_ls", "pyright", "ts_ls", "clangd", "bashls",
        },
        automatic_installation = true,
      })
    end,
  },
  {
    "neovim/nvim-lspconfig",
    config = function()
      local lspconfig = require("lspconfig")
      local on_attach = function(client, bufnr)
        local opts = { buffer = bufnr, remap = false }
        vim.keymap.set("n", "gd", vim.lsp.buf.definition, opts)
        vim.keymap.set("n", "K", vim.lsp.buf.hover, opts)
        vim.keymap.set("n", "gi", vim.lsp.buf.implementation, opts)
        vim.keymap.set("n", "gr", vim.lsp.buf.references, opts)
        vim.keymap.set("n", "<leader>rn", vim.lsp.buf.rename, opts)
        vim.keymap.set({ "n", "v" }, "<leader>ca", vim.lsp.buf.code_action, opts)
      end
      local capabilities = require("cmp_nvim_lsp").default_capabilities()

      -- Set up each LSP server that has no special config
      local servers = { "lua_ls", "pyright", "ts_ls", "clangd", "bashls" }
      for _, server in ipairs(servers) do
        local cfg = {
          on_attach = on_attach,
          capabilities = capabilities,
        }
        local ok, _ = pcall(lspconfig[server].setup, cfg)
        if not ok then
          vim.notify("Failed to setup " .. server, vim.log.levels.WARN)
        end
      end
    end,
    dependencies = { "hrsh7th/cmp-nvim-lsp" },
  },
  {
    "hrsh7th/nvim-cmp",
    dependencies = {
      "hrsh7th/cmp-nvim-lsp",
      "L3MON4D3/LuaSnip",
      "saadparwaiz1/cmp_luasnip",
      "hrsh7th/cmp-buffer",
      "hrsh7th/cmp-path",
      "hrsh7th/cmp-cmdline",
    },
    config = function()
      local cmp = require("cmp")
      local luasnip = require("luasnip")
      cmp.setup({
        snippet = {
          expand = function(args)
            luasnip.lsp_expand(args.body)
          end,
        },
        mapping = cmp.mapping.preset.insert({
          ["<C-b>"] = cmp.mapping.scroll_docs(-4),
          ["<C-f>"] = cmp.mapping.scroll_docs(4),
          ["<C-Space>"] = cmp.mapping.complete(),
          ["<C-e>"] = cmp.mapping.abort(),
          ["<CR>"] = cmp.mapping.confirm({ select = true }),
          ["<Tab>"] = cmp.mapping(function(fallback)
            if cmp.visible() then
              cmp.select_next_item()
            elseif luasnip.expand_or_jumpable() then
              luasnip.expand_or_jump()
            else
              fallback()
            end
          end, { "i", "s" }),
          ["<S-Tab>"] = cmp.mapping(function(fallback)
            if cmp.visible() then
              cmp.select_prev_item()
            elseif luasnip.jumpable(-1) then
              luasnip.jump(-1)
            else
              fallback()
            end
          end, { "i", "s" }),
        }),
        sources = cmp.config.sources({
          { name = "nvim_lsp" },
          { name = "luasnip" },
        }, {
          { name = "buffer" },
          { name = "path" },
        }),
      })
      cmp.setup.cmdline({ "/", "?" }, {
        mapping = cmp.mapping.preset.cmdline(),
        sources = { { name = "buffer" } },
      })
      cmp.setup.cmdline(":", {
        mapping = cmp.mapping.preset.cmdline(),
        sources = cmp.config.sources({
          { name = "path" },
        }, {
          { name = "cmdline" },
        }),
      })
    end,
  },
  {
    "lewis6991/gitsigns.nvim",
    config = function()
      require("gitsigns").setup({
        signs = {
          add = { text = "┃" },
          change = { text = "┃" },
          delete = { text = "_" },
          topdelete = { text = "‾" },
          changedelete = { text = "~" },
        },
        on_attach = function(bufnr)
          local gs = package.loaded.gitsigns
          local function map(mode, l, r, opts)
            opts = opts or {}
            opts.buffer = bufnr
            vim.keymap.set(mode, l, r, opts)
          end
          map("n", "]c", function()
            if vim.wo.diff then return "]c" end
            vim.schedule(function() gs.next_hunk() end)
            return "<Ignore>"
          end, { expr = true })
          map("n", "[c", function()
            if vim.wo.diff then return "[c" end
            vim.schedule(function() gs.prev_hunk() end)
            return "<Ignore>"
          end, { expr = true })
        end,
      })
    end,
  },
})

-- General settings
vim.opt.number = true
vim.opt.relativenumber = true
vim.opt.expandtab = true
vim.opt.shiftwidth = 2
vim.opt.tabstop = 2
vim.opt.softtabstop = 2
vim.opt.smartindent = true
vim.opt.mouse = "a"
vim.opt.clipboard = "unnamedplus"
vim.opt.ignorecase = true
vim.opt.smartcase = true
vim.opt.termguicolors = true
vim.opt.signcolumn = "yes"
vim.opt.updatetime = 250
vim.opt.timeoutlen = 300

-- Leader key
vim.g.mapleader = " "
vim.g.maplocalleader = " "

-- Keymaps
vim.keymap.set("n", "<leader>ff", "<cmd>Telescope find_files<cr>")
vim.keymap.set("n", "<leader>fg", "<cmd>Telescope live_grep<cr>")
vim.keymap.set("n", "<leader>fb", "<cmd>Telescope buffers<cr>")
vim.keymap.set("n", "<leader>fh", "<cmd>Telescope help_tags<cr>")
vim.keymap.set("n", "<leader>e", vim.diagnostic.open_float)
vim.keymap.set("n", "[d", vim.diagnostic.goto_prev)
vim.keymap.set("n", "]d", vim.diagnostic.goto_next)
"""


class NvimModule(BaseModule):
    """Installs Neovim, ripgrep, fd-find, and deploys a full lazy.nvim configuration."""

    name: str = "nvim"

    def install(self) -> bool:
        """Install Neovim + companions, deploy config, and sync plugins.

        Returns:
            True if installation and plugin sync succeed, False otherwise.
        """
        if not apt_install(["neovim", "ripgrep", "fd-find"]):
            logger.error("Failed to install Neovim packages via apt.")
            return False

        if not which("nvim"):
            logger.error("nvim not found after installation.")
            return False

        # Ensure fd is accessible as 'fd' (Ubuntu package is 'fdfind')
        fd_find = which("fdfind")
        fd = which("fd")
        if fd_find and not fd:
            run_command(
                ["sudo", "ln", "-sf", str(fd_find), "/usr/local/bin/fd"],
                capture=True,
                check=False,
            )

        # Deploy Neovim config
        self._deploy_config()

        # Run headless Lazy sync to pre-install plugins
        logger.info("Running Lazy sync (headless) — this may take a while...")
        sync_result = run_command(
            ["nvim", "--headless", "+Lazy! sync", "+qa"],
            capture=True,
            check=False,
            timeout=600,
        )
        if sync_result.returncode != 0:
            logger.warning(
                f"Lazy sync exited with code {sync_result.returncode}. "
                "Plugins may not be fully installed."
            )
        else:
            logger.info("Lazy sync completed successfully.")

        # Run headless checkhealth to confirm
        health_result = run_command(
            ["nvim", "--headless", "+checkhealth", "+qa"],
            capture=True,
            check=False,
            timeout=120,
        )
        if health_result.returncode == 0:
            logger.info("Neovim checkhealth passed.")
        else:
            logger.warning("Neovim checkhealth reported issues.")

        return True

    def verify(self) -> list[CheckResult]:
        """Verify Neovim, ripgrep, fd-find, and config are in place.

        Returns:
            List of CheckResult objects.
        """
        results: list[CheckResult] = []

        nvim_path = which("nvim")
        if nvim_path:
            ver = run_command(["nvim", "--version"], capture=True, check=False)
            first_line = (ver.stdout or "").split("\n")[0].strip()
            results.append(
                CheckResult(
                    name="neovim installed",
                    passed=True,
                    message=first_line or f"Found at {nvim_path}",
                )
            )
        else:
            results.append(
                CheckResult(
                    name="neovim installed",
                    passed=False,
                    message="nvim not found.",
                    fix="Run: sudo apt install neovim",
                )
            )

        rg_path = which("rg")
        results.append(
            CheckResult(
                name="ripgrep installed",
                passed=rg_path is not None,
                message=f"Found at {rg_path}" if rg_path else "ripgrep not found.",
                fix=None if rg_path else "Run: sudo apt install ripgrep",
            )
        )

        fd_path = which("fd") or which("fdfind")
        results.append(
            CheckResult(
                name="fd-find installed",
                passed=fd_path is not None,
                message=f"Found at {fd_path}" if fd_path else "fd-find not found.",
                fix=None if fd_path else "Run: sudo apt install fd-find",
            )
        )

        init_exists = INIT_LUA_PATH.exists()
        results.append(
            CheckResult(
                name="nvim config deployed",
                passed=init_exists,
                message=f"Config at {INIT_LUA_PATH}" if init_exists else "init.lua not found.",
                fix=None if init_exists else "Run: devpilot setup nvim",
            )
        )

        return results

    def doctor(self) -> list[CheckResult]:
        """Run comprehensive health checks for Neovim.

        Returns:
            List of CheckResult objects (delegates to verify).
        """
        return self.verify()

    def _deploy_config(self) -> None:
        """Write the lazy.nvim init.lua to ~/.config/nvim/init.lua."""
        NVIM_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        INIT_LUA_PATH.write_text(INIT_LUA_CONTENT, encoding="utf-8")
        logger.info(f"Neovim config deployed to {INIT_LUA_PATH}.")
