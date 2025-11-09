import sys
import time
import argparse
import logging

PYTHON_VERSION_REQUIREMENT = (3, 9)

# Configure logging for the application
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Check Python version to give a helpful message.
# This must be done before importing AU2 files because type hints can cause errors in old Python versions.
if not sys.version_info >= PYTHON_VERSION_REQUIREMENT:
    print(f"Error: AU2 requires Python {'.'.join(str(x) for x in PYTHON_VERSION_REQUIREMENT)} or above. "
          f"You are using Python {'.'.join(str(x) for x in sys.version_info)}.")
    time.sleep(100)
    exit()

# Now it's safe to import AU2 specific modules
from AU2.frontends.inquirer_cli import main as cli_main
from AU2.database.setup import db_session
from AU2.database.model.Assassin import Assassin
# Assuming an email utility function exists for sending 'UPDATES ONLY' emails.
from AU2.utils.email_sender import send_updates_only_email


def send_updates_only_emails_logic():
    """
    Identifies assassins who qualify for an 'UPDATES ONLY' email and sends it.
    An assassin qualifies if they have new targets OR if their competency deadline
    has been extended or newly set since the last email notification.
    After sending, updates the `last_emailed_competency_deadline` for relevant assassins.
    """
    logging.info("Starting 'UPDATES ONLY' email sending process.")

    emailed_assassins_count = 0
    deadline_updated_assassins_count = 0
    session = db_session() # Obtain a session from the factory/scoped session

    try:
        # Fetch all active assassins from the database
        assassins = session.query(Assassin).filter(Assassin.active == True).all()
        logging.info(f"Found {len(assassins)} active assassins to check.")

        for assassin in assassins:
            reasons = []

            # Condition 1: Assassin has new targets
            if assassin.has_new_targets():
                reasons.append("new targets assigned")
                logging.debug(f"Assassin {assassin.id} ({assassin.name}): New targets detected.")

            # Condition 2: Competency deadline has been extended or newly set
            if assassin.competency_deadline is not None:
                if assassin.last_emailed_competency_deadline is None:
                    reasons.append("competency deadline set for the first time")
                    logging.debug(f"Assassin {assassin.id} ({assassin.name}): Competency deadline set initially to {assassin.competency_deadline}.")
                elif assassin.competency_deadline > assassin.last_emailed_competency_deadline:
                    reasons.append("competency deadline extended")
                    logging.debug(f"Assassin {assassin.id} ({assassin.name}): Competency deadline extended from {assassin.last_emailed_competency_deadline} to {assassin.competency_deadline}.")
            
            if reasons:
                logging.info(f"Preparing 'UPDATES ONLY' email for Assassin {assassin.id} ({assassin.name}) due to: {', '.join(reasons)}")
                try:
                    # Attempt to send the email
                    send_updates_only_email(assassin)
                    emailed_assassins_count += 1
                    logging.info(f"Successfully sent 'UPDATES ONLY' email to Assassin {assassin.id} ({assassin.name}).")

                    # If email sending was successful, update the deadline watermark.
                    # This change will be staged in the session and committed at the end.
                    if assassin.last_emailed_competency_deadline != assassin.competency_deadline:
                        assassin.last_emailed_competency_deadline = assassin.competency_deadline
                        deadline_updated_assassins_count += 1
                        logging.debug(f"Staged update for last_emailed_competency_deadline for Assassin {assassin.id} ({assassin.name}) to {assassin.competency_deadline}.")

                except Exception as e:
                    logging.error(f"Failed to send 'UPDATES ONLY' email to Assassin {assassin.id} ({assassin.name}): {e}", exc_info=True)
                    # Do not update the deadline if email sending fails.
                    # We continue to the next assassin, leaving previously staged changes intact.
            else:
                logging.debug(f"Assassin {assassin.id} ({assassin.name}): No updates found to trigger an 'UPDATES ONLY' email.")

        # Commit all successful updates to the database in a single transaction.
        session.commit()
        logging.info(f"Finished 'UPDATES ONLY' email sending process. {emailed_assassins_count} emails sent. "
                     f"{deadline_updated_assassins_count} assassins had their last_emailed_competency_deadline updated.")

    except Exception as e:
        logging.error(f"An unexpected error occurred during 'UPDATES ONLY' email sending process: {e}", exc_info=True)
        session.rollback() # Rollback any pending changes in case of a catastrophic error
    finally:
        session.close() # Always close the session

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="AU2 Application Main Entry Point")
    parser.add_argument(
        '--send-update-emails',
        action='store_true',
        help="Run the logic to send 'UPDATES ONLY' emails to assassins based on target and competency deadline changes."
    )
    args = parser.parse_args()

    if args.send_update_emails:
        send_updates_only_emails_logic()
    else:
        # Default behavior: launch the interactive CLI
        try:
            cli_main()
        except Exception as e:
            # Replicate original error handling for CLI mode
            print(e)
            time.sleep(100)