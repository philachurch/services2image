#!/usr/bin/env python3
"""This module generates an image file for future planning center dates"""

import sys
import os
from datetime import datetime
import requests
import imgkit
from requests.auth import HTTPBasicAuth
from jinja2 import Environment, FileSystemLoader

APPLICATION_ID = os.environ.get('PC_ID')
APPLICATION_SECRET = os.environ.get('PC_SECRET')
PC_BASE_URL = 'https://api.planningcenteronline.com/services/v2/'

auth = HTTPBasicAuth(APPLICATION_ID, APPLICATION_SECRET)
env = Environment(loader=FileSystemLoader('templates'), autoescape=True)
schedule_template = env.get_template('schedule.html')


def epoch(date):
    """Return epoch time for a planning center date
    """
    return datetime.strptime(date, '%B %d, %Y').timestamp()


def get_service_types():
    """Get all service types
    """
    service_types_response = requests.get(
        PC_BASE_URL + 'service_types', auth=auth)
    service_types = []
    for service_type in service_types_response.json()['data']:
        service_types.append(service_type)
    return service_types


def get_plans(service_type_id):
    """Get all future plans for a service type
    """
    plans_response = requests.get(
        PC_BASE_URL +
        f'service_types/{service_type_id}/plans?filter=future',
        auth=auth)
    plans = []
    for plan in plans_response.json()['data']:
        plans.append(plan)
    return plans


def get_team_members(service_type_id, plan_id, filter_position):
    """Get all team members for a plan and filtered by position name
    """
    members_response = requests.get(
        PC_BASE_URL +
        f'service_types/{service_type_id}/plans/{plan_id}/team_members',
        auth=auth)
    members = []
    for member in members_response.json()['data']:
        position = member['attributes']['team_position_name']
        status = member['attributes']['status']
        name = member['attributes']['name']
        status = member['attributes']['status']

        if position:
            if filter_position in position.lower():
                members.append(
                    {'name': name, 'position': position, 'status': status})
    return sorted(members, key=lambda x: x['position'])


def get_services(filter_position):
    """Combine plans and members into a list
    """
    future_dates = []
    for service_type in get_service_types():
        for plan in get_plans(service_type['id']):
            members = get_team_members(service_type['id'], plan['id'], filter_position)
            date = plan['attributes']['dates']
            epoch_time = epoch(date)
            service_title = plan['attributes']['title']
            stype = service_type['attributes']['name']
            future_dates.append({'date': date,
                                 'epoch': epoch_time,
                                 'title': service_title,
                                 'type': stype,
                                 'members': members})
    return sorted(future_dates, key=lambda x: x['epoch'])


def generate_schedule_image(output_file, filter_position):
    """Create an image file with the latest schedule
    """
    # get current time
    current_time = datetime.now().strftime('%m/%d/%Y %H:%M:%S')

    # get all services with positions that include audio in them
    services = get_services(filter_position)

    # generate html
    generated_html = schedule_template.render(
        services=services, time=current_time)

    # turn html into an image
    options = {'quality': '100'}
    imgkit.from_string(generated_html, output_file, options=options)


# no fancy argument handling, oh well
if len(sys.argv) == 3 and APPLICATION_ID and APPLICATION_SECRET:
    filterp = sys.argv[1]
    target = sys.argv[2]
    generate_schedule_image(target, filterp)
else:
    print('PC_ID="applicationid" PC_SECRET="applicationsecret" ./services2image.py audio out.png')
