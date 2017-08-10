# -*- coding: utf-8 -*-
# from da
from flask import request, session, current_app as app
from decimal import ROUND_HALF_UP, Decimal

from wtforms import Form, StringField, DecimalField
from wtforms.validators import ValidationError, DataRequired
from datetime import datetime
from pytz import timezone
import wtforms_json

from openprocurement.auction.utils import prepare_extra_journal_fields
from openprocurement.auction.dutch.constants import DUTCH, SEALEDBID, BESTBID
from openprocurement.auction.dutch.utils import lock_bids

wtforms_json.init()


def validate_bid_value(form, field):
    """
    On Dutch Phase: Bid must be equal current dutch amount.
    On Sealed Bids Phase: Bid must be greater then current dutch amount.
    On Best Bid Phase: Bid must be greater then current dutch amount.
    """
    phase = form.document.get('current_phase')
    if phase == DUTCH:
        try:
            current_amount = form.document['stages'][form.document['current_stage']].get(
                'amount',
            )
            if not isinstance(current_amount, Decimal):
                current_amount = Decimal(str(current_amount))
            if current_amount != field.data:
                message = u"Passed value doesn't match current amount={}".format(current_amount)
                # form[field.name].errors.append(message)
                raise ValidationError(message)
            return True
        except KeyError as e:
            form[field.name].errors.append(e.message)
            raise e
    elif phase == BESTBID:
        # TODO: one percent step validation
        pass
    else:
        if field.data <= 0.0 and field.data != -1:
            message = u'To low value'
            form[field.name].errors.append(message)
            raise ValidationError(message)
        dutch_winner_value = form.auction_document['results'].get(DUTCH, {}).get('value')

        if not isinstance(dutch_winner_value, Decimal):
            dutch_winner_value = Decimal(str(dutch_winner_value))
        if field.data != -1 and (field.data <= dutch_winner_value):
            message = u'Bid value can\'t be less or equal current amount'
            form[field.name].errors.append(message)
            raise ValidationError(message)
    return True


def validate_bidder_id(form, field):
    phase = form.document.get('current_phase')
    if phase == BESTBID:
        try:
            dutch_winner = form.auction_document['results'].get(DUTCH, {})
            if dutch_winner and dutch_winner['id'] != field.data:
                message = u'bidder_id don\'t match with dutchWinner.bidder_id'
                form[field.name].errors.append(message)
                raise ValidationError(message)
            return True
        except KeyError as e:
            form[field.name].errors.append(e)
            raise e
    elif phase.startswith('pre'):
        raise ValidationError('Not allowed to post bid on current phase {}'.format(
            phase
        ))
    else:
        return True
        # for bidder_data in form.auction.bidders_data:
        #     if bidder_data['id'] == field.data:
        #         dutch_winner = getattr(form.auction, 'dutch_winner', {})
        #         if dutch_winner.get('id') == field.data:
        #             message = u'Not allowd to post bid for dutch winner'
        #             form[field.name].error.append(message)
        #             raise ValidationError(message)
        #         return True
        raise ValidationError("Unauthorized bidder id={}".format(field.data))
    raise ValidationError("Unknown error")


class BidsForm(Form):
    bidder_id = StringField(
        'bidder_id',
        validators=[
            DataRequired(message=u'No bidder id'),
            validate_bidder_id
        ]
    )
    bid = DecimalField(
        'bid',
        places=2,
        rounding=ROUND_HALF_UP,
        validators=[
            DataRequired(message=u'Bid amount is required'),
            validate_bid_value
        ]
    )


def form_handler():
    auction = app.config['auction']
    form = app.bids_form.from_json(request.json)
    form.auction = auction
    form.document = auction.auction_document
    current_time = datetime.now(timezone('Europe/Kiev'))
    current_phase = form.document.get('current_phase')
    document = auction.auction_document
    if not form.validate():
        app.logger.info(
            "Bidder {} with client_id {} wants place bid {} in {}on phase {} "
            "with errors {}".format(
                request.json.get('bidder_id', 'None'), session.get('client_id', ''),
                request.json.get('bid', 'None'), current_time.isoformat(),
                current_phase, repr(form.errors)),
            extra=prepare_extra_journal_fields(request.headers))
        return {'status': 'failed', 'errors': form.errors}
    if current_phase == DUTCH:
        with lock_bids(auction):
            ok = auction.add_dutch_winner({
                'amount': document['stages'][document['current_stage']]['amount'],
                'time': current_time.isoformat(),
                'bidder_id': form.data['bidder_id']
            })
            if not isinstance(ok, Exception):
                app.logger.info(
                    "Bidder {} with client {} has won dutch on value {}".format(
                        form.data['bidder_id'],
                        session.get('client_id'),
                        form.data['bid']
                    )
                )
                return {"status": "ok", "data": form.data}
            else:
                app.logger.info(
                    "Bidder {} with client_id {} wants place bid {} in {} on dutch "
                    "with errors {}".format(
                        request.json.get('bidder_id', 'None'),
                        session.get('client_id'),
                        request.json.get('bid', 'None'), current_time.isoformat(),
                        repr(ok)
                    ),
                    extra=prepare_extra_journal_fields(request.headers)
                )
                return {"status": "failed", "errors": [repr(ok)]}

    elif current_phase == SEALEDBID:
        pass
        # auction.requests_queue.put(request)
        # try:
        #     form_result = _process_form(form)
        #         if form_result['status'] == 'ok':
        #             auction.add_bid((
        #                 form.document['current_stage'],
        #                 {
        #                     'amount': form.data['bid'],
        #                     'bidder_id': form.data['bidder_id'],
        #                     'time': current_time.isoformat()
        #                 }
        #             ))
        #     except:
        #         app.logger.critical('Error while processing request')
        #         form.bid.errors.append('Internal server error')
        #         form_result = {
        #             'status': 'failed',
        #             'errors': form.errors
        #         }
        #     auction.requests_queue.get()
        #     return form_result
    else:
        return {
            'status': 'failed',
            'errors': {
                'form': ['Bids period expired.']
            }
        }
