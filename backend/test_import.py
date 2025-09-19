try:
    from app.workers.pipeline import process_check
    print('Import successful')
    print(f'process_check: {process_check}')
except Exception as e:
    import traceback
    print(f'Import failed: {e}')
    print(f'Traceback: {traceback.format_exc()}')