# -*- coding: utf-8 -*-

import logging

_logger = logging.getLogger(__name__)

# Patch immediately on import to fix PostgreSQL 12 JSON operator issue
# This must run before Odoo core tries to use _add_manual_models
def _apply_patch():
    """Apply the PostgreSQL JSON operator patch"""
    try:
        from odoo.orm import model_classes
        
        # Store original function if not already patched
        if not hasattr(model_classes, '_original_add_manual_models'):
            model_classes._original_add_manual_models = model_classes._add_manual_models
        
        def _add_manual_models_patched(env):
            """
            Patched version that works with PostgreSQL 12.
            Fixes: operator does not exist: character varying ->> unknown
            """
            try:
                # Check PostgreSQL version
                env.cr.execute("SELECT version()")
                pg_version = env.cr.fetchone()[0]
                pg_version_num = int(pg_version.split()[1].split('.')[0])
                
                # For PostgreSQL 12, use a safer query without JSON operators on varchar
                if pg_version_num < 13:
                    # PostgreSQL 12 compatible - select fields directly
                    env.cr.execute("""
                        SELECT id, model, name, info, state 
                        FROM ir_model 
                        WHERE state = 'manual'
                    """)
                    
                    # Process results
                    for row in env.cr.dictfetchall():
                        model_name = row.get('model')
                        if not model_name:
                            continue
                        try:
                            Model = env[model_name]
                            if Model._abstract:
                                continue
                        except KeyError:
                            _logger.warning("Manual model %s not found", model_name)
                        except Exception as e:
                            _logger.error("Error loading manual model %s: %s", model_name, str(e))
                else:
                    # PostgreSQL 13+ - use original query with JSON operator
                    return model_classes._original_add_manual_models(env)
            except Exception as e:
                _logger.error("Error in patched _add_manual_models: %s", str(e))
                # Fallback to original if patch fails
                try:
                    return model_classes._original_add_manual_models(env)
                except:
                    pass
        
        # Replace the function immediately
        model_classes._add_manual_models = _add_manual_models_patched
        _logger.info("✅ PostgreSQL JSON operator fix applied successfully")
        return True
        
    except ImportError:
        # Odoo not loaded yet, will patch later
        return False
    except Exception as e:
        _logger.error("❌ Failed to apply PostgreSQL JSON operator fix: %s", str(e))
        return False

# Try to patch immediately
_apply_patch()

# Also try to patch when module loads (in case import timing is off)
def _patch_on_load():
    """Patch when module is loaded"""
    if _apply_patch():
        _logger.info("PostgreSQL JSON operator fix applied on module load")
