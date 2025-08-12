from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Tuple
from collections import defaultdict
import sys
import time
import random


# 가능한 주사위 규칙들을 나타내는 enum
class DiceRule(Enum):
    ONE = 0
    TWO = 1
    THREE = 2
    FOUR = 3
    FIVE = 4
    SIX = 5
    CHOICE = 6
    FOUR_OF_A_KIND = 7
    FULL_HOUSE = 8
    SMALL_STRAIGHT = 9
    LARGE_STRAIGHT = 10
    YACHT = 11


# 입찰 방법을 나타내는 데이터클래스
@dataclass
class Bid:
    group: str  # 입찰 그룹 ('A' 또는 'B')
    amount: int  # 입찰 금액


# 주사위 배치 방법을 나타내는 데이터클래스
@dataclass
class DicePut:
    rule: DiceRule  # 배치 규칙
    dice: List[int]  # 배치할 주사위 목록


# 팀의 현재 상태를 관리하는 클래스
class GameState:
    def __init__(self):
        self.dice = []  # 현재 보유한 주사위 목록
        self.rule_score: List[Optional[int]] = [
            None
        ] * 12  # 각 규칙별 획득 점수 (사용하지 않았다면 None)
        self.bid_score = 0  # 입찰로 얻거나 잃은 총 점수

    def get_total_score(self) -> int:
        """현재까지 획득한 총 점수 계산 (상단/하단 점수 + 보너스 + 입찰 점수)"""
        basic = bonus = combination = 0

        # 기본 점수 규칙 계산 (ONE ~ SIX)
        basic = sum(score for score in self.rule_score[0:6] if score is not None)
        bonus = 35000 if basic >= 63000 else 0
        combination = sum(score for score in self.rule_score[6:12] if score is not None)

        return basic + bonus + combination + self.bid_score

    def bid(self, is_successful: bool, amount: int):
        """입찰 결과에 따른 점수 반영"""
        if is_successful:
            self.bid_score -= amount  # 성공시 베팅 금액만큼 점수 차감
        else:
            self.bid_score += amount  # 실패시 베팅 금액만큼 점수 획득

    def add_dice(self, new_dice: List[int]):
        """새로운 주사위들을 보유 목록에 추가"""
        self.dice.extend(new_dice)

    def use_dice(self, put: DicePut):
        """주사위를 사용하여 특정 규칙에 배치"""
        # 이미 사용한 규칙인지 확인
        assert (
            put.rule is not None and self.rule_score[put.rule.value] is None
        ), "Rule already used"

        # 주사위 제거 전에 로그 출력
        print(f"# Debug: Removing dice {put.dice} from {self.dice}", file=sys.stderr)
        
        for d in put.dice:
            # 주사위 목록에 있는 주사위 제거
            if d in self.dice:
                self.dice.remove(d)
            else:
                print(f"# Debug: Dice {d} not found in {self.dice}", file=sys.stderr)
                # 주사위가 없으면 에러 대신 무시
                continue

        # 해당 규칙의 점수 계산 및 저장
        assert put.rule is not None
        self.rule_score[put.rule.value] = self.calculate_score(put)

    @staticmethod
    def calculate_score(put: DicePut) -> int:
        """규칙에 따른 점수를 계산하는 함수"""
        rule, dice = put.rule, put.dice

        # 기본 규칙 점수 계산 (해당 숫자에 적힌 수의 합 × 1000점)
        if rule == DiceRule.ONE:
            return sum(d for d in dice if d == 1) * 1000
        if rule == DiceRule.TWO:
            return sum(d for d in dice if d == 2) * 1000
        if rule == DiceRule.THREE:
            return sum(d for d in dice if d == 3) * 1000
        if rule == DiceRule.FOUR:
            return sum(d for d in dice if d == 4) * 1000
        if rule == DiceRule.FIVE:
            return sum(d for d in dice if d == 5) * 1000
        if rule == DiceRule.SIX:
            return sum(d for d in dice if d == 6) * 1000
        if rule == DiceRule.CHOICE:  # 주사위에 적힌 모든 수의 합 × 1000점
            return sum(dice) * 1000
        if (
            rule == DiceRule.FOUR_OF_A_KIND
        ):  # 같은 수가 적힌 주사위가 4개 있다면, 주사위에 적힌 모든 수의 합 × 1000점, 아니면 0
            ok = any(dice.count(i) >= 4 for i in range(1, 7))
            return sum(dice) * 1000 if ok else 0
        if (
            rule == DiceRule.FULL_HOUSE
        ):  # 3개의 주사위에 적힌 수가 서로 같고, 다른 2개의 주사위에 적힌 수도 서로 같으면 주사위에 적힌 모든 수의 합 × 1000점, 아닐 경우 0점
            pair = triple = False
            for i in range(1, 7):
                cnt = dice.count(i)
                # 5개 모두 같은 숫자일 때도 인정
                if cnt == 2 or cnt == 5:
                    pair = True
                if cnt == 3 or cnt == 5:
                    triple = True
            return sum(dice) * 1000 if pair and triple else 0
        if (
            rule == DiceRule.SMALL_STRAIGHT
        ):  # 4개의 주사위에 적힌 수가 1234, 2345, 3456중 하나로 연속되어 있을 때, 15000점, 아닐 경우 0점
            e1, e2, e3, e4, e5, e6 = [dice.count(i) > 0 for i in range(1, 7)]
            ok = (
                (e1 and e2 and e3 and e4)
                or (e2 and e3 and e4 and e5)
                or (e3 and e4 and e5 and e6)
            )
            return 15000 if ok else 0
        if (
            rule == DiceRule.LARGE_STRAIGHT
        ):  # 5개의 주사위에 적힌 수가 12345, 23456중 하나로 연속되어 있을 때, 30000점, 아닐 경우 0점
            e1, e2, e3, e4, e5, e6 = [dice.count(i) > 0 for i in range(1, 7)]
            ok = (e1 and e2 and e3 and e4 and e5) or (e2 and e3 and e4 and e5 and e6)
            return 30000 if ok else 0
        if (
            rule == DiceRule.YACHT
        ):  # 5개의 주사위에 적힌 수가 모두 같을 때 50000점, 아닐 경우 0점
            ok = any(dice.count(i) == 5 for i in range(1, 7))
            return 50000 if ok else 0

        assert False, "Invalid rule"


# 게임 상태를 관리하는 클래스
class Game:
    def __init__(self):
        self.my_state = GameState()  # 내 팀의 현재 상태
        self.opp_state = GameState()  # 상대 팀의 현재 상태
        self.current_round = 0  # 현재 턴 번호 (1번쨰가 1턴)
        self.opponent_bids = {}  # 상대방의 각 턴별 입찰 가격 저장 (0번쨰가 1턴)
        self.start_time = time.time()  # 게임 시작 시간
        self.opponent_yacht_completed = False  # 상대방이 YACHT를 완성했는지 여부
        self.my_yacht_completed = False  # 내가 YACHT를 완성했는지 여부



    def get_max_duplicate_count(self, dice_group: List[int]) -> dict:
        """주사위 그룹에서 중복된 숫자들을 딕셔너리 형태로 반환하는 함수 (사용 가능한 규칙만 고려)"""
        counts = [0] * 7  # 1~6까지의 개수 (인덱스 0은 사용하지 않음)
        
        # 각 숫자의 개수 세기
        for dice in dice_group:
            counts[dice] += 1
        
        # SMALL_STRAIGHT, LARGE_STRAIGHT, YACHT가 모두 달성되었는지 확인
        small_straight_completed = self.my_state.rule_score[DiceRule.SMALL_STRAIGHT.value] is not None
        large_straight_completed = self.my_state.rule_score[DiceRule.LARGE_STRAIGHT.value] is not None
        yacht_completed = self.my_state.rule_score[DiceRule.YACHT.value] is not None
        high_rules_completed = small_straight_completed and large_straight_completed and yacht_completed
        
        # 사용 가능한 기본 규칙들만 고려 (이미 달성한 규칙은 제외)
        # 중복된 숫자들을 딕셔너리로 반환 (2개 이상인 것만)
        duplicate_dict = {}
        
        if high_rules_completed:
            # 고점수 규칙들이 달성된 경우: 큰 수부터 우선순위 (6 > 5 > 4 > 3 > 2 > 1)
            for num in range(6, 0, -1):  # 6부터 1까지 역순
                rule_index = num - 1  # 6→5(SIX), 5→4(FIVE), ..., 1→0(ONE)
                # 해당 규칙이 아직 사용되지 않았고, 고점수 규칙들이 모두 달성된 상태에서만 고려
                if self.my_state.rule_score[rule_index] is None and counts[num] >= 2:
                    duplicate_dict[num] = counts[num]
        else:
            # 기존 로직: 사용 가능한 규칙 중 2개 이상 중복된 숫자들을 딕셔너리로 반환
            for num in range(1, 7):
                rule_index = num - 1  # 1→0(ONE), 2→1(TWO), ..., 6→5(SIX)
                # 해당 규칙이 아직 사용되지 않았고 2개 이상 중복된 경우만 고려
                if self.my_state.rule_score[rule_index] is None and counts[num] >= 2:
                    duplicate_dict[num] = counts[num]
        
        return duplicate_dict

    def save_opponent_bid(self, round_num: int, bid_amount: int):
        """상대방의 입찰 가격을 저장하는 함수"""
        self.opponent_bids[round_num] = bid_amount

    def check_opponent_yacht_completion(self):
        """상대방이 YACHT를 완성했는지 확인하는 함수"""
        # 상대방이 YACHT 규칙을 사용했는지 확인
        if self.opp_state.rule_score[DiceRule.YACHT.value] is not None:
            if self.opp_state.rule_score[DiceRule.YACHT.value] > 0:
                self.opponent_yacht_completed = True

    def check_my_yacht_completion(self):
        """내가 YACHT를 완성했는지 확인하는 함수"""
        # 내가 YACHT 규칙을 사용했는지 확인
        if self.my_state.rule_score[DiceRule.YACHT.value] is not None:
            if self.my_state.rule_score[DiceRule.YACHT.value] > 0:
                self.my_yacht_completed = True

    def should_block_yacht(self, dice_a: List[int], dice_b: List[int]) -> Optional[Tuple[str, int]]:
        """YACHT 방해가 필요한지 확인하는 함수"""
        # 상대방이 이미 YACHT를 완성했다면 방해하지 않음
        if self.opponent_yacht_completed:
            return None
        
        # 상대방이 4개 중복을 가지고 있는지 확인
        # 현재 나와있는 A, B 그룹 + 상대 보유패에서 동일한 숫자 5개가 되는지 확인하는 로직
        opp_dice = self.opp_state.dice
        if len(opp_dice) < 4:
            return None
        
        # A그룹과 B그룹 각각에 대해 상대방 보유패와 합쳐서 YACHT 가능성 확인
        for group_name, dice_group in [("A", dice_a), ("B", dice_b)]:
            # 상대방 보유패 + 해당 그룹의 다이스를 합쳐서 계산
            combined_dice = opp_dice + dice_group
            combined_counts = [0] * 7
            
            for dice in combined_dice:
                combined_counts[dice] += 1
            
            # YACHT가 가능한 숫자가 있는지 확인 (5개 이상)
            for num in range(1, 7):
                if combined_counts[num] >= 5:
                    count_a = dice_a.count(num)
                    count_b = dice_b.count(num)
                    
                    # 해당 숫자를 얻을 수 있는 그룹이 하나만 있는지 확인
                    if (count_a > 0 and count_b == 0) or (count_a == 0 and count_b > 0):
                        target_group = "A" if count_a > 0 else "B"
                        return (target_group, 5001)
        
        return None


    def calculate_rule_potential_score(self, dice: List[int], rule: DiceRule) -> int:
        """특정 규칙에 대한 잠재적 점수 계산"""
        if rule == DiceRule.ONE:
            return sum(d for d in dice if d == 1) * 1000
        elif rule == DiceRule.TWO:
            return sum(d for d in dice if d == 2) * 1000
        elif rule == DiceRule.THREE:
            return sum(d for d in dice if d == 3) * 1000
        elif rule == DiceRule.FOUR:
            return sum(d for d in dice if d == 4) * 1000
        elif rule == DiceRule.FIVE:
            return sum(d for d in dice if d == 5) * 1000
        elif rule == DiceRule.SIX:
            return sum(d for d in dice if d == 6) * 1000
        elif rule == DiceRule.CHOICE:
            return sum(dice) * 1000
        elif rule == DiceRule.FOUR_OF_A_KIND:
            if any(dice.count(i) >= 4 for i in range(1, 7)):
                return sum(dice) * 1000
            return 0
        elif rule == DiceRule.YACHT and not self.my_yacht_completed:
            if any(dice.count(i) == 5 for i in range(1, 7)):
                return 50000
        elif rule == DiceRule.FULL_HOUSE:
            # FULL_HOUSE: 3개 + 2개 조합 (서로 다른 숫자여야 함)
            # 먼저 3개가 되는 숫자를 찾고, 그 숫자를 제외한 나머지에서 2개가 되는 숫자를 찾음
            triple_number = None
            for i in range(1, 7):
                if dice.count(i) >= 3:
                    triple_number = i
                    break
            
            if triple_number is None:
                return 0  # 3개가 되는 숫자가 없음
            
            # 3개가 되는 숫자를 제외한 나머지 주사위들
            remaining_dice = [d for d in dice if d != triple_number]
            
            # 남은 주사위들에서 2개가 되는 숫자가 있는지 확인
            has_pair = any(remaining_dice.count(i) >= 2 for i in range(1, 7))
            
            if has_pair:
                return sum(dice) * 1000
            return 0
        elif rule == DiceRule.SMALL_STRAIGHT:
            has = [False] * 7
            for d in dice:
                has[d] = True
            if ((has[1] and has[2] and has[3] and has[4]) or
                (has[2] and has[3] and has[4] and has[5]) or
                (has[3] and has[4] and has[5] and has[6])):
                return 15000
            return 0
        elif rule == DiceRule.LARGE_STRAIGHT:
            has = [False] * 7
            for d in dice:
                has[d] = True
            if ((has[1] and has[2] and has[3] and has[4] and has[5]) or
                (has[2] and has[3] and has[4] and has[5] and has[6])):
                return 30000
            return 0
        return 0

    def calculate_highest_possible_score_for_last_turn(self, dice_group: List[int]) -> int:
        """마지막 턴에서 10개 주사위(보유 5개 + 그룹 5개)를 2개 규칙에 최적으로 배분했을 때의 최고 점수 계산"""
        # 내가 보유한 주사위와 그룹 주사위를 합쳐서 10개 주사위 생성
        combined_dice = self.my_state.dice + dice_group
        
        # 남은 규칙들 찾기 (2개만 남아있음)
        remaining_rules = []
        for i in range(12):
            if self.my_state.rule_score[i] is None:
                remaining_rules.append(DiceRule(i))
        
        if len(remaining_rules) != 2:
            return 0  # 2개가 아니면 0 반환
        
        rule1, rule2 = remaining_rules[0], remaining_rules[1]
        
        # 10개 주사위를 2개 규칙에 배분하는 모든 경우의 수 계산
        max_score = 0
        
        # 규칙1에 5개, 규칙2에 5개 배분
        for i in range(len(combined_dice) - 4):  # 첫 번째 주사위 선택
            for j in range(i + 1, len(combined_dice) - 3):  # 두 번째 주사위 선택
                for k in range(j + 1, len(combined_dice) - 2):  # 세 번째 주사위 선택
                    for l in range(k + 1, len(combined_dice) - 1):  # 네 번째 주사위 선택
                        for m in range(l + 1, len(combined_dice)):  # 다섯 번째 주사위 선택
                            # 규칙1에 배분할 5개 주사위
                            dice_for_rule1 = [combined_dice[i], combined_dice[j], combined_dice[k], combined_dice[l], combined_dice[m]]
                            # 규칙2에 배분할 나머지 5개 주사위
                            dice_for_rule2 = [d for idx, d in enumerate(combined_dice) if idx not in [i, j, k, l, m]]
                            
                            # 각 규칙의 점수 계산
                            score1 = self.calculate_rule_potential_score(dice_for_rule1, rule1)
                            score2 = self.calculate_rule_potential_score(dice_for_rule2, rule2)
                            
                            total_score = score1 + score2
                            max_score = max(max_score, total_score)
        
        return max_score

    def calculate_strategic_bid_amount(self, selected_dice: List[int]) -> int:
        """전략적 입찰 금액을 계산하는 함수"""
        max_count_dict = self.get_max_duplicate_count(selected_dice) 
        dice_sum = sum(selected_dice)
        
        # 딕셔너리에서 최대 중복 개수 추출
        max_count = max(max_count_dict.values()) if max_count_dict else 0

        if self.current_round <= 1:
            # 첫 번째 턴: 중복 개수와 합계를 고려한 전략적 입찰
            if max_count == 5:
                return 7999  # YACHT 가능성
            elif max_count == 4:
                return 4001  # FOUR_OF_A_KIND 가능성
            elif max_count == 3:
                return 2001  # FULL_HOUSE 가능성
            elif max_count == 2: # 기본 중복
                if dice_sum >= 21: # 합계 높으면 더 높은 금액 입찰
                    return 988 
                elif dice_sum >= 17:
                    return 498
                return 2
            else:
                # 중복이 없어도 높은 합계면 입찰
                return 3002 if dice_sum >= 20 else 1
        
        elif self.current_round <= 3:
            # 1, 2, 3 번째 턴: 중복되는게 4개 이상인지 확인
            if max_count >= 4:
                if dice_sum >= 21: # 합계 높으면 더 높은 금액 입찰 (44445)
                    return 4501
                if dice_sum >= 17: # 합계 높으면 더 높은 금액 입찰 (33335)
                    return 3155
                return 2401
            elif max_count == 3: # 기본 중복
                if dice_sum >= 22: # 합계 높으면 더 높은 금액 입찰 (44455)
                    return 2301  
                if dice_sum >= 19: # 합계 높으면 더 높은 금액 입찰 (33355)
                    return 1897
                return 1245
            elif max_count == 2: # 기본 중복
                if dice_sum >= 21: # 합계 높으면 더 높은 금액 입찰 (55443)
                    return 1135
                if dice_sum >= 16: # (44332) 
                    return 874 
                return 2
            else: #중복 없음
                if dice_sum >= 20: # 합계 높으면 더 높은 금액 입찰 (23456)
                    return 786  
                return 487
        
        elif 4 <= self.current_round <= 8:
            # 4~8턴: 중복 수에 따른 전략적 입찰
            # 내가 YACHT를 완성했다면 0 또는 (최소 입찰 - 1) 중 랜덤 선택
            if self.my_yacht_completed:
                min_opponent_bid = min(self.opponent_bids.values())
                option1 = 0
                option2 = min(511, max(0, min_opponent_bid - 1))
                
                # 50% 확률로 0 또는 (최소 입찰 + 1) 선택
                return random.choice([option1, option2])
            
            # YACHT를 완성하지 못했다면, 5개 완성이 목표
            min_opponent_bid = min(self.opponent_bids.values()) # 현재까지 상대 배팅 최솟값
            # max_opponent_bid = max(self.opponent_bids.values()) # 현재까지 상대 배팅 최댓값
            
            # 내가 보유한 주사위와 선택한 그룹의 주사위를 합쳐서 중복 수 계산
            combined_dice = self.my_state.dice + selected_dice
            combined_max_count_dict = self.get_max_duplicate_count(combined_dice)
            
            # 딕셔너리에서 최대 중복 개수 추출
            combined_max_count = max(combined_max_count_dict.values()) if combined_max_count_dict else 0
            
            if combined_max_count == 3:
                # 중복수가 3개인 카드가 나오면 (최소 입찰 - 1) 선택
                return min(499, max(0, min_opponent_bid - 1))
            elif combined_max_count == 4:
                # 중복수가 4개인 카드가 나오면 (최소 입찰 + 1) 선택
                return min(511, max(0, min_opponent_bid + 1))
            else:
                # (6, 6) 체크
                if selected_dice.count(6) >= 2:
                    return min(599, max(0, min_opponent_bid - 1))
                
                # (5, 5) 체크
                if selected_dice.count(5) >= 2:
                    return min(599, max(0, min_opponent_bid - 1))
                
                # (6, 5) 체크 (6과 5가 각각 1개 이상)
                if selected_dice.count(6) >= 1 and selected_dice.count(5) >= 1:
                    return min(599, max(0, min_opponent_bid - 1))
                
                # 그 외 0
                return 0
        
        elif self.current_round >= 9:
            # 9턴부터: 내가 필요한 숫자와 상대방이 필요한 숫자 기반 전략적 입찰
            
            # 내가 필요한 숫자들을 계산
            my_needed_dice_value = self.calculate_my_needed_dice_value(selected_dice)
            
            # 상대방이 필요한 숫자들을 계산
            opp_needed_dice_value = self.calculate_opponent_needed_dice_value(selected_dice)
            
            min_opponent_bid = min(self.opponent_bids.values())
            
            if my_needed_dice_value > 0:
                # 내가 필요한 숫자가 있으면 해당 그룹에 강하게 배팅
                if my_needed_dice_value >= 51:  # 매우 높은 가치
                    return min(2999, max(min_opponent_bid, 1999))
                elif my_needed_dice_value >= 42:  # 높은 가치
                    return min(1999, max(min_opponent_bid, 999))
                elif my_needed_dice_value >= 33:  # 중간 가치
                    return min(999, max(min_opponent_bid, 99))
                else:  # 낮은 가치
                    return min(1, max(min_opponent_bid , 2))
            elif opp_needed_dice_value > 0:
                # 내가 필요한 숫자가 없고 상대방이 필요한 숫자가 있으면 방해 배팅
                if opp_needed_dice_value >= 10:  # 높은 가치
                    return min(3499, max(min_opponent_bid, 2999))
                elif opp_needed_dice_value >= 5:  # 중간 가치
                    return min(2499, max(min_opponent_bid, 1999))
                else:  # 낮은 가치
                    return min(1499, max(min_opponent_bid, 999))
            else:
                # 둘 다 필요한 숫자가 없으면 기본 전략
                option1 = 0
                option2 = min(2, max(0, min_opponent_bid + 1))
                return random.choice([option1, option2])
        
        else:
            return 1  # 기본값


    def should_use_rule_strategically(self, rule: DiceRule, score: int) -> bool:
        """현재 턴과 상황에 따라 규칙을 전략적으로 사용할지 결정하는 함수"""
        
        # 1. YACHT 규칙: 매우 높은 점수이므로 조건이 맞으면 사용
        if rule == DiceRule.YACHT:
            return score > 0  # YACHT가 가능하면 무조건 사용
        
        # 2. LARGE_STRAIGHT: 높은 점수이므로 조건이 맞으면 사용
        if rule == DiceRule.LARGE_STRAIGHT:
            return score > 0  # LARGE_STRAIGHT가 가능하면 사용
        
        # 3. SMALL_STRAIGHT: 중간 점수이므로 전략적 판단
        if rule == DiceRule.SMALL_STRAIGHT:
            if score > 0:  # 완성된 스트레이트 (15000점)
                return True  # 완성된 스트레이트는 언제든 사용
            else:  # 불완전한 스트레이트 - 초반에만 시도
                return self.current_round <= 6
        
        # 4. FOUR_OF_A_KIND: 높은 점수이므로 조건이 맞으면 사용 (9라운드 이후에는 무조건 사용)
        if rule == DiceRule.FOUR_OF_A_KIND:
            if self.current_round >= 9:
                return score > 0  # 9라운드 이후에는 점수만 체크 (1111이어도 사용)
            else:
                return score > 0
        
        # 5. FULL_HOUSE: 중간 점수이므로 전략적 판단 (9라운드 이후에는 무조건 사용)
        if rule == DiceRule.FULL_HOUSE:
            if self.current_round >= 9:
                return score > 0  # 9라운드 이후에는 점수만 체크 (작은 숫자여도 사용)
            elif self.current_round <= 6:  # 초반에는 아껴두기
                return score > 0 and self.current_round >= 4
            else:  # 후반에는 사용
                return score > 0
        
        # 6. CHOICE: 13턴 이후에만 고려 (이미 find_optimal_dice_for_rule에서 처리됨)
        if rule == DiceRule.CHOICE:
            return self.current_round >= 13 and score - 7000 > 0
        
        # 7. 기본 규칙들 (ONE~SIX): 각 규칙별로 다른 점수 임계값 적용
        if rule == DiceRule.ONE:
            # ONE: 1이 3개 이상이면 사용 (3000점 이상)
            if score >= 3000:
                return True
            elif score >= 1000:  # 1이 2개인 경우
                return self.current_round >= 7
            else:  # 1이 1개인 경우
                return self.current_round >= 10
        
        elif rule == DiceRule.TWO:
            # TWO: 2가 3개 이상이면 사용 (6000점 이상)
            if score >= 6000:
                return True
            elif score >= 2000:  # 2가 2개인 경우
                return self.current_round >= 6
            else:  # 2가 1개인 경우
                return self.current_round >= 9
        
        elif rule == DiceRule.THREE:
            # THREE: 3이 3개 이상이면 사용 (9000점 이상)
            if score >= 9000:
                return True
            elif score >= 3000:  # 3이 2개인 경우
                return self.current_round >= 6
            else:  # 3이 1개인 경우
                return self.current_round >= 8
        
        elif rule == DiceRule.FOUR:
            # FOUR: 4가 3개 이상이면 사용 (12000점 이상)
            if score >= 12000:
                return True
            elif score >= 4000:  # 4가 2개인 경우
                return self.current_round >= 4
            else:  # 4가 1개인 경우
                return self.current_round >= 7
        
        elif rule == DiceRule.FIVE:
            # FIVE: 5가 3개 이상이면 사용 (15000점 이상)
            if score >= 15000:
                return True
            elif score >= 5000:  # 5가 2개인 경우
                return self.current_round >= 3
            else:  # 5가 1개인 경우
                return self.current_round >= 6
        
        elif rule == DiceRule.SIX:
            # SIX: 6이 3개 이상이면 사용 (18000점 이상)
            if score >= 18000:
                return True
            elif score >= 6000:  # 6이 2개인 경우
                return self.current_round >= 3
            else:  # 6이 1개인 경우
                return self.current_round >= 5
        
        return True  # 기본적으로는 사용

    # ================================ [필수 구현] ================================
    # ============================================================================
    # 주사위가 주어졌을 때, 어디에 얼마만큼 베팅할지 정하는 함수
    # 입찰할 그룹과 베팅 금액을 pair로 묶어서 반환
    # ============================================================================
    def calculate_bid(self, dice_a: List[int], dice_b: List[int]) -> Bid:
        # 13라운드 특별 전략: 남은 규칙에 필요한 숫자에 따른 배팅
        if self.current_round == 13:
            # 마지막 턴 특별 전략: 남은 규칙이 2개일 때 10개 주사위를 최적으로 배분
            remaining_rules_count = sum(1 for score in self.my_state.rule_score if score is None)
            if remaining_rules_count == 2:
                # 각 그룹에서 10개 주사위를 2개 규칙에 최적으로 배분했을 때의 최고 점수 계산
                score_a = self.calculate_highest_possible_score_for_last_turn(dice_a)
                score_b = self.calculate_highest_possible_score_for_last_turn(dice_b)
                
                # 더 높은 점수를 얻을 수 있는 그룹 선택
                if score_a > score_b:
                    selected_dice = dice_a
                    group = "A"
                elif score_b > score_a:
                    selected_dice = dice_b
                    group = "B"
                else:
                    # 점수가 같으면 합이 큰 그룹 선택
                    if sum(dice_a) >= sum(dice_b):
                        selected_dice = dice_a
                        group = "A"
                    else:
                        selected_dice = dice_b
                        group = "B"
                
                # 3. 턴별 전략적 입찰 금액 계산
                amount = self.calculate_strategic_bid_amount(selected_dice)
                return Bid(group, amount)
            return self.calculate_final_round_bid(dice_a, dice_b)
        
        # 1. YACHT 방해가 필요한지 먼저 확인
        block_result = self.should_block_yacht(dice_a, dice_b)
        if block_result is not None:
            block_group, block_result_amount = block_result
    
            return Bid(block_group, block_result_amount)
        
        
        
        # 2. n턴 이후에는 남은 룰을 바탕으로 필요한 중복 숫자 우선 고려
        if self.current_round >= 6:  # 6턴 이후부터는 전략적 선택
            # ONE, TWO 규칙을 아직 사용하지 않았다면 1, 2가 많은 그룹 우선 고려
            if (self.my_state.rule_score[DiceRule.ONE.value] is None or 
                self.my_state.rule_score[DiceRule.TWO.value] is None):
                
                # 1, 2의 개수 계산 (내가 보유한 주사위 + 그룹 주사위)
                count_1_a = dice_a.count(1) + self.my_state.dice.count(1)
                count_2_a = dice_a.count(2) + self.my_state.dice.count(2)
                count_1_b = dice_b.count(1) + self.my_state.dice.count(1)
                count_2_b = dice_b.count(2) + self.my_state.dice.count(2)
                
                # ONE이 남아있고 1이 4개 이상이면 우선 선택
                if (self.my_state.rule_score[DiceRule.ONE.value] is None and 
                    count_1_a >= 4 and count_1_a > count_1_b):
                    selected_dice = dice_a
                    group = "A"
                    
                elif (self.my_state.rule_score[DiceRule.ONE.value] is None and 
                    count_1_b >= 4 and count_1_b > count_1_a):
                    selected_dice = dice_b
                    group = "B"
                    
                # TWO가 남아있고 2가 4개 이상이면 우선 선택
                elif (self.my_state.rule_score[DiceRule.TWO.value] is None and 
                    count_2_a >= 4 and count_2_a > count_2_b):
                    selected_dice = dice_a
                    group = "A"
                    
                elif (self.my_state.rule_score[DiceRule.TWO.value] is None and 
                    count_2_b >= 4 and count_2_b > count_2_a):
                    selected_dice = dice_b
                    group = "B"
                    
                else:
                    # ONE/TWO 우선순위가 적용되지 않으면 기존 로직 사용
                    # 각 그룹에서 내게 필요한 숫자들의 가치 계산
                    value_a = self.calculate_my_needed_dice_value(dice_a)
                    value_b = self.calculate_my_needed_dice_value(dice_b)
                    
                    # 가치가 높은 그룹 선택 (필요한 숫자가 더 많은 그룹)
                    if value_a > value_b:
                        selected_dice = dice_a
                        group = "A"
                    elif value_b > value_a:
                        selected_dice = dice_b
                        group = "B"
                    else:
                        # 가치가 같다면 중복과 합을 고려
                        max_count_a_dict = self.get_max_duplicate_count(dice_a)
                        max_count_b_dict = self.get_max_duplicate_count(dice_b)
                        dice_Asum = sum(dice_a)
                        dice_Bsum = sum(dice_b)
                        
                        # 딕셔너리에서 최대 중복 개수 추출
                        max_count_a = max(max_count_a_dict.values()) if max_count_a_dict else 0
                        max_count_b = max(max_count_b_dict.values()) if max_count_b_dict else 0
                        
                        # 중복이 같다면, 합이 큰 것 선택
                        if max_count_a >= max_count_b:
                            if dice_Asum >= dice_Bsum:
                                selected_dice = dice_a
                                group = "A"
                            else:
                                selected_dice = dice_b
                                group = "B"
                        else:
                            selected_dice = dice_b
                            group = "B"
            else:
                # ONE, TWO 규칙이 모두 사용되었으면 기존 로직 사용
                # 각 그룹에서 내게 필요한 숫자들의 가치 계산
                value_a = self.calculate_my_needed_dice_value(dice_a)
                value_b = self.calculate_my_needed_dice_value(dice_b)
                
                # 가치가 높은 그룹 선택 (필요한 숫자가 더 많은 그룹)
                if value_a > value_b:
                    selected_dice = dice_a
                    group = "A"
                elif value_b > value_a:
                    selected_dice = dice_b
                    group = "B"
                else:
                    # 가치가 같다면 중복과 합을 고려
                    max_count_a_dict = self.get_max_duplicate_count(dice_a)
                    max_count_b_dict = self.get_max_duplicate_count(dice_b)
                    dice_Asum = sum(dice_a)
                    dice_Bsum = sum(dice_b)
                    
                    # 딕셔너리에서 최대 중복 개수 추출
                    max_count_a = max(max_count_a_dict.values()) if max_count_a_dict else 0
                    max_count_b = max(max_count_b_dict.values()) if max_count_b_dict else 0
                    
                    # 중복이 같다면, 합이 큰 것 선택
                    if max_count_a >= max_count_b:
                        if dice_Asum >= dice_Bsum:
                            selected_dice = dice_a
                            group = "A"
                        else:
                            selected_dice = dice_b
                            group = "B"
                    else:
                        selected_dice = dice_b
                        group = "B"
        else:
            # 1-5턴: 기존 로직 (중복이 더 많은 그룹 선택)
            max_count_a_dict = self.get_max_duplicate_count(dice_a)
            max_count_b_dict = self.get_max_duplicate_count(dice_b)
            dice_Asum = sum(dice_a)
            dice_Bsum = sum(dice_b)
            
            # 딕셔너리에서 최대 중복 개수 추출
            max_count_a = max(max_count_a_dict.values()) if max_count_a_dict else 0
            max_count_b = max(max_count_b_dict.values()) if max_count_b_dict else 0
            
            # 중복이 같다면, 합이 큰 것 선택
            if max_count_a >= max_count_b:
                if dice_Asum >= dice_Bsum:
                    selected_dice = dice_a
                    group = "A"
                else:
                    selected_dice = dice_b
                    group = "B"
            else:
                selected_dice = dice_b
                group = "B"

        # 3. 턴별 전략적 입찰 금액 계산
        amount = self.calculate_strategic_bid_amount(selected_dice)
        
        return Bid(group, amount)

    def calculate_final_round_bid(self, dice_a: List[int], dice_b: List[int]) -> Bid:
        """13라운드에서 남은 규칙에 필요한 숫자를 찾아서 전략적 배팅"""
        
        # 남은 규칙들 찾기
        remaining_rules = []
        for i in range(12):  # 0~11 (총 12개 규칙)
            if self.my_state.rule_score[i] is None:
                remaining_rules.append(DiceRule(i))
        
        if not remaining_rules:
            # 남은 규칙이 없으면 기본 로직
            group = "A" if sum(dice_a) >= sum(dice_b) else "B"
            return Bid(group, 0)
        
        # 각 그룹에서 필요한 숫자들의 총 가치 계산
        value_a = self.calculate_needed_dice_value(dice_a, remaining_rules, is_opponent=False)
        value_b = self.calculate_needed_dice_value(dice_b, remaining_rules, is_opponent=False)
        
        if value_a > value_b:
            group = "A"
            # 필요한 숫자들의 가치 * 999
            amount = min(999, value_a * 999)
        elif value_b > value_a:
            group = "B"
            amount = min(999, value_b * 999)
        else:
            # 동일하면 더 높은 합을 가진 그룹
            group = "A" if sum(dice_a) >= sum(dice_b) else "B"
            amount = min(999, max(value_a, value_b) * 999)
        

        return Bid(group, amount)

    def calculate_needed_dice_value(self, dice_group: List[int], remaining_rules: List[DiceRule], is_opponent: bool = False) -> int:
        """특정 주사위 그룹에서 남은 규칙들에 필요한 숫자들의 총 가치 계산"""
        # 상대방과 내 것의 로직을 분리하여 가치 계산
        if is_opponent:
            # 상대방의 경우: dice_group과 상대방이 보유한 주사위를 합쳐서 계산
            combined_dice = dice_group + self.opp_state.dice
        else:
            # 내 것의 경우: dice_group과 내가 보유한 주사위를 합쳐서 계산
            combined_dice = dice_group + self.my_state.dice
        
        total_value = 0
        
        for rule in remaining_rules:
            if rule in [DiceRule.ONE, DiceRule.TWO, DiceRule.THREE, DiceRule.FOUR, DiceRule.FIVE, DiceRule.SIX]:
                # 기본 규칙들: 해당 숫자의 개수 (dice_group만 고려)
                target_number = rule.value + 1  # ONE=0→1, TWO=1→2, ...
                count = dice_group.count(target_number)
                total_value += count * target_number  # 개수 * 숫자
                
            elif rule == DiceRule.CHOICE:
                # CHOICE: 모든 숫자가 유용함 (dice_group만 고려)
                total_value += sum(dice_group)
                
            elif rule == DiceRule.FOUR_OF_A_KIND:
                # FOUR_OF_A_KIND: 4개 이상 있는 숫자 (combined_dice 고려)
                for num in range(4, 7):  # 4,5,6만 고려
                    if combined_dice.count(num) >= 4:
                        total_value += num * 4  # 해당 숫자 * 4
                        
            elif rule == DiceRule.FULL_HOUSE:
                # FULL_HOUSE: 3개+2개 조합이 가능한 숫자들 (combined_dice 고려)
                for num1 in range(4, 7):  # 4,5,6만 고려
                    if combined_dice.count(num1) >= 3:
                        for num2 in range(4, 7):
                            if num2 != num1 and combined_dice.count(num2) >= 2:
                                total_value += (num1 * 3) + (num2 * 2)
                                
            elif rule == DiceRule.SMALL_STRAIGHT:
                # SMALL_STRAIGHT: 연속된 4개 숫자 (combined_dice 고려)
                unique_nums = set(combined_dice)
                straights = [
                    {1, 2, 3, 4}, {2, 3, 4, 5}, {3, 4, 5, 6}
                ]
                for straight in straights:
                    if straight.issubset(unique_nums):
                        total_value += 15
                        
            elif rule == DiceRule.LARGE_STRAIGHT:
                # LARGE_STRAIGHT: 연속된 5개 숫자 (combined_dice 고려)
                unique_nums = set(combined_dice)
                straights = [
                    {1, 2, 3, 4, 5}, {2, 3, 4, 5, 6}
                ]
                for straight in straights:
                    if straight.issubset(unique_nums):
                        total_value += 30
                        
            elif rule == DiceRule.YACHT:
                # YACHT: 5개가 모두 같은 숫자 (combined_dice 고려)
                for num in range(1, 7):
                    if combined_dice.count(num) >= 5:
                        total_value += 50
        
        return total_value

    def calculate_my_needed_dice_value(self, dice_group: List[int]) -> int:
        """내가 필요한 숫자들을 계산하는 함수"""
        # 내가 사용하지 않은 규칙들 찾기
        remaining_rules = []
        for i in range(12):  # 0~11 (총 12개 규칙)
            if self.my_state.rule_score[i] is None:
                remaining_rules.append(DiceRule(i))
        
        return self.calculate_needed_dice_value(dice_group, remaining_rules, is_opponent=False)

    def calculate_opponent_needed_dice_value(self, dice_group: List[int]) -> int:
        """상대방이 필요한 숫자들을 계산하는 함수"""
        # 상대방이 사용하지 않은 규칙들 찾기
        remaining_rules = []
        for i in range(12):  # 0~11 (총 12개 규칙)
            if self.opp_state.rule_score[i] is None:
                remaining_rules.append(DiceRule(i))
        
        return self.calculate_needed_dice_value(dice_group, remaining_rules, is_opponent=True)

    # ============================================================================
    # 주어진 주사위에 대해 사용할 규칙과 주사위를 정하는 함수
    # 사용할 규칙과 사용할 주사위의 목록을 pair로 묶어서 반환
    # ============================================================================
    def calculate_put(self) -> DicePut:
        # 정렬된 주사위를 한 번만 계산하여 저장 (중복 제거된 버전과 단순 정렬된 변수)
        self.sorted_dice_unique = sorted(set(self.my_state.dice))
        self.sorted_dice = sorted(self.my_state.dice, reverse=True)
        
        # 사용하지 않은 규칙들 찾기
        unused_rules = [i for i, score in enumerate(self.my_state.rule_score) if score is None]
        
        best_rule = None
        best_dice = None
        best_score = -1

        if self.current_round >= 12:
            # 13턴 특별 로직: 2개의 RULE만 남아있는데, 여기서 10개의 주사위로 가능한 조합중에 가장 최고의 점수가 나오는 조합으로 5개, 5개씩 해야돼
            # 남은 규칙들 찾기 (2개만 남아있음)
            remaining_rules = []
            for i in range(12):
                if self.my_state.rule_score[i] is None:
                    remaining_rules.append(DiceRule(i))
            
            if len(remaining_rules) == 2:
                rule1, rule2 = remaining_rules[0], remaining_rules[1]
                
                # 10개 주사위를 2개 규칙에 배분하는 모든 경우의 수 계산
                max_score = 0
                best_dice_for_rule1 = []
                best_dice_for_rule2 = []
                
                # 규칙1에 5개, 규칙2에 5개 배분
                for i in range(len(self.my_state.dice) - 4):  # 첫 번째 주사위 선택
                    for j in range(i + 1, len(self.my_state.dice) - 3):  # 두 번째 주사위 선택
                        for k in range(j + 1, len(self.my_state.dice) - 2):  # 세 번째 주사위 선택
                            for l in range(k + 1, len(self.my_state.dice) - 1):  # 네 번째 주사위 선택
                                for m in range(l + 1, len(self.my_state.dice)):  # 다섯 번째 주사위 선택
                                    # 규칙1에 배분할 5개 주사위
                                    dice_for_rule1 = [self.my_state.dice[i], self.my_state.dice[j], self.my_state.dice[k], self.my_state.dice[l], self.my_state.dice[m]]
                                    # 규칙2에 배분할 나머지 5개 주사위
                                    dice_for_rule2 = [d for idx, d in enumerate(self.my_state.dice) if idx not in [i, j, k, l, m]]
                                    
                                    # 각 규칙의 점수 계산
                                    score1 = self.calculate_rule_potential_score(dice_for_rule1, rule1)
                                    score2 = self.calculate_rule_potential_score(dice_for_rule2, rule2)
                                    
                                    total_score = score1 + score2
                                    if total_score > max_score:
                                        max_score = total_score
                                        best_dice_for_rule1 = dice_for_rule1
                                        best_dice_for_rule2 = dice_for_rule2
                
                # 최고 점수를 내는 조합으로 첫 번째 규칙 사용
                if best_dice_for_rule1 and best_dice_for_rule2:
                    return DicePut(rule1, best_dice_for_rule1)
            
        # 일반적인 우선순위 규칙 (13턴이 아니거나 CHOICE가 이미 사용된 경우)
        if self.current_round > 8:
            # 8턴 이후: 기본규칙은 낮은 숫자부터 우선순위 적용
            priority_rules = [
                DiceRule.YACHT.value,           # 50000점
                DiceRule.LARGE_STRAIGHT.value,  # 30000점
                DiceRule.SMALL_STRAIGHT.value,  # 15000점
                DiceRule.FOUR_OF_A_KIND.value,  # 높은 점수
                DiceRule.FULL_HOUSE.value,      # 높은 점수
                DiceRule.CHOICE.value,          # 높은 점수
                DiceRule.ONE.value,             # 기본 규칙 (낮은 숫자부터)
                DiceRule.TWO.value,
                DiceRule.THREE.value,
                DiceRule.FOUR.value,
                DiceRule.FIVE.value,
                DiceRule.SIX.value,             # 기본 규칙 (높은 숫자)
            ]
        else:
            # 8턴 이전: 기존 우선순위 유지
            priority_rules = [
                DiceRule.YACHT.value,           # 50000점
                DiceRule.LARGE_STRAIGHT.value,  # 30000점
                DiceRule.SMALL_STRAIGHT.value,  # 15000점
                DiceRule.FOUR_OF_A_KIND.value,  # 높은 점수
                DiceRule.FULL_HOUSE.value,      # 높은 점수
                DiceRule.CHOICE.value,          # 높은 점수
                DiceRule.SIX.value,             # 기본 규칙 (높은 숫자)
                DiceRule.FIVE.value,
                DiceRule.FOUR.value,
                DiceRule.THREE.value,
                DiceRule.TWO.value,
                DiceRule.ONE.value,             # 기본 규칙 (낮은 숫자)
            ]
        
        # 고점수 특수 규칙 완성 후 낮은 숫자 정리 전략
        high_value_rules_completed = (
            self.my_yacht_completed and 
            self.my_state.rule_score[DiceRule.LARGE_STRAIGHT.value] is not None and
            self.my_state.rule_score[DiceRule.SMALL_STRAIGHT.value] is not None
        )
        
        if high_value_rules_completed and self.current_round < 9:
            # 9라운드 전에만 1,2,3이 3개 이상 있으면 우선적으로 정리 (점수 무시)
            for low_num in [1, 2, 3]:
                count = self.my_state.dice.count(low_num)
                if count >= 3:  # 3개 이상이면 정리 대상
                    rule_index = low_num - 1  # 1→0(ONE), 2→1(TWO), 3→2(THREE)
                    if rule_index in unused_rules:
                        rule = DiceRule(rule_index)
                        dice, score = self.find_optimal_dice_for_rule(rule)
                        
            
                        return DicePut(rule, dice)
        
        elif self.my_yacht_completed and self.current_round < 9:
            # 9라운드 전에만 YACHT만 완성된 경우: 4개 이상의 낮은 숫자만 정리
            for low_num in [1, 2, 3]:
                count = self.my_state.dice.count(low_num)
                if count >= 4:
                    rule_index = low_num - 1  # 1→0(ONE), 2→1(TWO), 3→2(THREE)
                    if rule_index in unused_rules:
                        rule = DiceRule(rule_index)
                        dice, score = self.find_optimal_dice_for_rule(rule)
                        
            
                        return DicePut(rule, dice)
        
        # 우선순위에 따라 규칙 검사
        for priority_rule in priority_rules:
            if priority_rule in unused_rules:
                rule = DiceRule(priority_rule)
                dice, score = self.find_optimal_dice_for_rule(rule)
                
                # CHOICE 규칙은 13번째 라운드에서만 사용
                if rule == DiceRule.CHOICE and self.current_round != 13:
                    continue
                
                # 현재 턴과 규칙에 따른 전략적 선택
                # TODO: 수정할 곳
                if self.should_use_rule_strategically(rule, score): # 사용할 수 있는 규칙이 있다면
                    # 불완전한 스트레이트의 경우 우선순위를 고려한 특별 처리
                    if rule in [DiceRule.SMALL_STRAIGHT, DiceRule.LARGE_STRAIGHT] and score == 0:
                        # 불완전한 스트레이트는 우선순위가 높으므로 기존 선택을 덮어씀
                        # 단, 이미 완성된 고점수 규칙(YACHT, 완성된 스트레이트)이 있다면 제외
                        if (best_rule is None or 
                            (best_rule not in [DiceRule.YACHT, DiceRule.LARGE_STRAIGHT, DiceRule.SMALL_STRAIGHT] or best_score == 0)):
            
                            best_score = score
                            best_rule = rule
                            best_dice = dice
                    elif score > best_score:
        
                        best_score = score
                        best_rule = rule
                        best_dice = dice
                else:
                    pass # 완성되는 규칙 없음
        
        # 전략적 선택이 없으면 모든 규칙을 점수 기반으로 검사
        if best_rule is None:
            for rule_index in unused_rules:
                rule = DiceRule(rule_index)
                dice, score = self.find_optimal_dice_for_rule(rule)
                
                if score > best_score:
                    best_score = score
                    best_rule = rule
                    best_dice = dice
        
        # 최적의 조합이 없으면 기본값 사용
        if best_rule is None:
            best_rule = DiceRule(unused_rules[0])
            best_dice = self.my_state.dice[:5] if len(self.my_state.dice) >= 5 else [0] * 5
        

        return DicePut(best_rule, best_dice)


    def find_optimal_dice_for_rule(self, rule: DiceRule) -> Tuple[List[int], int]:
        """규칙별 최적 주사위 조합 찾기"""
        # TODO: 수정 필요, 턴별로 IF문을 나누자
        my_dice = self.my_state.dice.copy()  # 복사본 사용
        
        # 기본 규칙들 (ONE~SIX): 해당 숫자를 최대한 많이 선택
        if rule in [DiceRule.ONE, DiceRule.TWO, DiceRule.THREE, DiceRule.FOUR, DiceRule.FIVE, DiceRule.SIX]:
            target_number = rule.value + 1  # ONE=0이므로 +1 (ONE→1, TWO→2, ..., SIX→6)
            target_count = my_dice.count(target_number)  # 정렬된 주사위 불필요, count 사용
            
            if target_count > 0:
                # 해당 숫자를 최대한 많이 선택 (최대 5개)
                dice = []
                temp_dice = my_dice.copy()
                
                # 해당 숫자들을 우선 선택
                for _ in range(min(5, target_count)):
                    dice.append(target_number)
                    temp_dice.remove(target_number)
                
                # 5개가 안 되면 나머지 주사위로 채움 (특별한 우선순위 적용)
                remaining_count = {}
                for d in temp_dice:
                    remaining_count[d] = remaining_count.get(d, 0) + 1
                
                # FOUR_OF_A_KIND, FULL_HOUSE가 아직 사용 가능한지 확인
                four_of_kind_available = self.my_state.rule_score[DiceRule.FOUR_OF_A_KIND.value] is None
                full_house_available = self.my_state.rule_score[DiceRule.FULL_HOUSE.value] is None
                high_rules_available = four_of_kind_available or full_house_available
                
                # 1순위: YACHT가 달성되고 FOUR_OF_A_KIND나 FULL_HOUSE가 사용 가능하면 가장 작은수를 사용
                yacht_completed = self.my_state.rule_score[DiceRule.YACHT.value] is not None
                if yacht_completed and high_rules_available and temp_dice:
                    temp_dice.sort()  # 작은 숫자부터 정렬
                    while len(dice) < 5 and temp_dice:
                        smallest = temp_dice.pop(0)  # 가장 작은 숫자 선택
                        dice.append(smallest)
                
                # 2순위: 9턴 이후에는 중복 상관없이 작은 수부터, 9턴 이전에는 중복이 없는 수들을 작은 수부터 선택
                if self.current_round >= 9:
                    # 9턴 이후: 중복 상관없이 작은 수부터 선택
                    temp_dice.sort()  # 작은 수부터 정렬
                    while len(dice) < 5 and temp_dice:
                        dice.append(temp_dice.pop(0))
                else:
                    # 9턴 이전: 중복이 없는 수들을 가장 작은 수부터 선택
                    unique_dice = [num for num, count in remaining_count.items() if count == 1 and num in temp_dice]
                    unique_dice.sort()  # 작은 수부터 정렬
                    
                    while len(dice) < 5 and unique_dice:
                        selected = unique_dice.pop(0)
                        # 9턴 이후부터 정렬
                        if self.current_round >= 9:
                            temp_dice.sort()
                        if selected in temp_dice:  # 아직 남아있는지 확인
                            dice.append(selected)
                            temp_dice.remove(selected)
                
                # 3순위: 나머지 주사위로 채움
                # 고점수 규칙들이 달성된 경우 작은 숫자부터 선택 (큰 숫자 보존)
                large_straight_completed = self.my_state.rule_score[DiceRule.LARGE_STRAIGHT.value] is not None
                small_straight_completed = self.my_state.rule_score[DiceRule.SMALL_STRAIGHT.value] is not None
                # LARGE_STRAIGHT, SMALL_STRAIGHT 둘 다 달성되면 6 보존
                straights_completed = large_straight_completed and small_straight_completed
                
                if straights_completed:
                    # 고점수 규칙 달성 시: 작은 숫자부터 선택 (큰 숫자 보존)
                    temp_dice.sort()  # 작은 숫자부터 정렬
                    while len(dice) < 5 and temp_dice:
                        dice.append(temp_dice.pop(0))  # 가장 작은 숫자부터 선택
                else:
                    # 기존 로직: 임의 순서
                    while len(dice) < 5 and temp_dice:
                        dice.append(temp_dice.pop(0))
                
                # 여전히 5개가 안 되면 남은 주사위 중에서 선택
                while len(dice) < 5 and temp_dice:
                    dice.append(temp_dice.pop(0))
                # 그래도 5개가 안 되면 기본값으로 채움 (실제 주사위 값 사용)
                while len(dice) < 5:
                    dice.append(my_dice[0] if my_dice else 1)
                
                score = self.calculate_rule_potential_score(dice, rule)
                return (dice, score)
        
        elif rule == DiceRule.CHOICE:
            # 10턴 이후에만 CHOICE 고려
            if self.current_round >= 10:
                # 가장 높은 숫자 5개 선택
                dice = self.sorted_dice[:5]
                score = self.calculate_rule_potential_score(dice, rule)
                return (dice, score)
            else:
                # 10턴 이전에는 CHOICE를 0점으로 처리
                return ([0] * 5, 0)
        
        elif rule == DiceRule.FOUR_OF_A_KIND:
            # 8라운드 전까지는 4,5,6으로만 구성된 경우에만 사용
            if self.current_round <= 8:
                # 8라운드 전: 4,5,6으로만 구성된 경우만 허용
                for num in range(4, 7):
                    count = my_dice.count(num)
                    if count >= 4:
                        # 실제 보유한 해당 숫자들을 사용
                        target_dice = []
                        temp_dice = my_dice.copy()
                        
                        # 해당 숫자 4개 사용
                        for i in range(4):
                            target_dice.append(num)
                            temp_dice.remove(num)
                        
                        # 나머지 1개는 다른 주사위 중에서 선택
                        if temp_dice:
                            target_dice.append(temp_dice[0])
                        else:
                            target_dice.append(num)  # 기본값
                        
                        score = self.calculate_rule_potential_score(target_dice, rule)
                        return (target_dice, score)
                
                # 8라운드 전에 4,5,6으로 조건 만족하지 않으면 0점
                return ([0] * 5, 0)
            
            else:
                # 8라운드 이후: 모든 숫자 허용
                for num in range(1, 7):
                    count = my_dice.count(num)
                    if count >= 4:
                        # 실제 보유한 해당 숫자들을 사용
                        target_dice = []
                        temp_dice = my_dice.copy()
                        
                        # 해당 숫자 4개 사용
                        for i in range(4):
                            target_dice.append(num)
                            temp_dice.remove(num)
                        
                        # 나머지 1개는 전략적으로 선택 (이미 사용한 규칙에 해당하는 숫자 우선)
                        if temp_dice:
                            # 이미 사용한 규칙에 해당하는 숫자들을 우선 선택
                            used_rule_dice = []
                            unused_rule_dice = []
                            
                            for die in temp_dice:
                                if die >= 1 and die <= 6:  # ONE~SIX 규칙에 해당
                                    rule_index = die - 1  # 0~5 인덱스
                                    if self.my_state.rule_score[rule_index] is not None:
                                        # 이미 사용한 규칙
                                        used_rule_dice.append(die)
                                    else:
                                        # 아직 사용하지 않은 규칙
                                        unused_rule_dice.append(die)
                                else:
                                    # 0이거나 다른 값
                                    unused_rule_dice.append(die)
                            
                            # 우선순위: 이미 사용한 규칙 > 사용하지 않은 규칙
                            if used_rule_dice:
                                # 이미 사용한 규칙 중 가장 높은 숫자 선택 (더 높은 점수 기대)
                                selected_die = max(used_rule_dice)
                            else:
                                # 사용하지 않은 규칙 중 가장 작은 숫자 선택
                                selected_die = min(unused_rule_dice) if unused_rule_dice else temp_dice[0]
                            
                            target_dice.append(selected_die)
                        else:
                            target_dice.append(num)  # 기본값
                        
                        score = self.calculate_rule_potential_score(target_dice, rule)
                        return (target_dice, score)
        
        elif rule == DiceRule.FULL_HOUSE:
            # 8라운드 전까지는 4,5,6으로만 구성된 경우에만 사용
            if self.current_round <= 8:
                # 8라운드 전: 4,5,6으로만 구성된 경우만 허용
                for num1 in range(4, 7):
                    count1 = my_dice.count(num1)
                    if count1 >= 3:
                        for num2 in range(4, 7):
                            if num2 != num1:
                                count2 = my_dice.count(num2)
                                if count2 >= 2:
                                    # 실제 보유한 주사위들로 조합 생성
                                    target_dice = []
                                    temp_dice = my_dice.copy()
                                    
                                    # 첫 번째 숫자 3개 사용
                                    for i in range(3):
                                        target_dice.append(num1)
                                        temp_dice.remove(num1)
                                    
                                    # 두 번째 숫자 2개 사용
                                    for i in range(2):
                                        target_dice.append(num2)
                                        temp_dice.remove(num2)
                                    
                                    score = self.calculate_rule_potential_score(target_dice, rule)
                                    return (target_dice, score)
                
                # 8라운드 전에 4,5,6으로 조건 만족하지 않으면 0점
                return ([0] * 5, 0)
            
            else:
                # 8라운드 이후: 모든 숫자 허용
                for num1 in range(1, 7):
                    count1 = my_dice.count(num1)
                    if count1 >= 3:
                        for num2 in range(1, 7):
                            if num2 != num1:
                                count2 = my_dice.count(num2)
                                if count2 >= 2:
                                    # 실제 보유한 주사위들로 조합 생성
                                    target_dice = []
                                    temp_dice = my_dice.copy()
                                    
                                    # 첫 번째 숫자 3개 사용
                                    for i in range(3):
                                        target_dice.append(num1)
                                        temp_dice.remove(num1)
                                    
                                    # 두 번째 숫자 2개 사용
                                    for i in range(2):
                                        target_dice.append(num2)
                                        temp_dice.remove(num2)
                                    
                                    score = self.calculate_rule_potential_score(target_dice, rule)
                                    return (target_dice, score)
        
        elif rule == DiceRule.SMALL_STRAIGHT:
            # 1234, 2345, 3456 중 하나 찾기
            sorted_dice = self.sorted_dice_unique
            
            # 완성된 스트레이트 확인
            sequences = [[1, 2, 3, 4], [2, 3, 4, 5], [3, 4, 5, 6]]
            
            for sequence in sequences:
                if all(x in sorted_dice for x in sequence):
                    # # 특별한 예외 처리: 3456 시퀀스에서 중복이 있는 경우 SMALL_STRAIGHT를 만들 수 없음
                    # # 예: 3,4,5,5,6이 있는 경우 3456으로는 SMALL_STRAIGHT를 만들 수 없음
                    # if sequence == [3, 4, 5, 6] and self.current_round <= 12:
                    #     # 3,4,5,6이 모두 있지만, 중복이 있는지 확인
                    #     dice_counts = {}
                    #     for die in my_dice:
                    #         dice_counts[die] = dice_counts.get(die, 0) + 1
                        
                    #     # 3,4,5,6 중에서 중복이 있는지 확인
                    #     has_duplicate_in_sequence = False
                    #     for num in [3, 4, 5, 6]:
                    #         if dice_counts.get(num, 0) > 1:
                    #             has_duplicate_in_sequence = True
                    #             break
                        
                    #     # 중복이 있으면 이 시퀀스는 건너뛰기
                    #     if has_duplicate_in_sequence:
                    #         continue
                    
                    # 완성된 스트레이트가 있으면 해당 숫자들만 선택
                    target_dice = []
                    temp_dice = my_dice.copy()
                    
                    for num in sequence:
                        if num in temp_dice:
                            target_dice.append(num)
                            temp_dice.remove(num)
                    
                    # 5번째는 남은 주사위 중에서 선택 (완성된 스트레이트인 경우만)
                    if temp_dice:
                        # 남은 주사위 중 가장 작은 수 선택
                        temp_dice.sort()
                        target_dice.append(temp_dice[0])
                    else:
                        target_dice.append(sequence[-1] + 1 if sequence[-1] < 6 else sequence[0] - 1)
                    
                    score = self.calculate_rule_potential_score(target_dice, rule)
                    return (target_dice, score)
            
            # 완성된 스트레이트가 없으면 가장 유력한 불완전 스트레이트 찾기
            best_partial = None
            best_count = 0
            
            for sequence in sequences:
                count = sum(1 for x in sequence if x in sorted_dice)
                if count > best_count:
                    best_count = count
                    best_partial = sequence
            
            # 불완전한 스트레이트가 있으면 해당 숫자들만 유지
            if best_partial and best_count >= 1:
                target_dice = []
                temp_dice = my_dice.copy()
                
                for num in best_partial:
                    if num in temp_dice:
                        target_dice.append(num)
                        temp_dice.remove(num)
                
                # 5개를 맞추기 위해 무작위 주사위 추가하지 않음
                # 필요한 숫자만 유지하여 다음 턴에서 완성 기회를 높임
                score = 0  # 불완전한 스트레이트는 0점
                return (target_dice, score)
            
        elif rule == DiceRule.LARGE_STRAIGHT:
            # 12345 또는 23456 찾기
            sorted_dice = self.sorted_dice_unique
            
            # 12345 찾기
            if all(x in sorted_dice for x in [1, 2, 3, 4, 5]):
                target_dice = []
                temp_dice = my_dice.copy()
                
                for num in [1, 2, 3, 4, 5]:
                    if num in temp_dice:
                        target_dice.append(num)
                        temp_dice.remove(num)
                
                score = self.calculate_rule_potential_score(target_dice, rule)
                return (target_dice, score)
            
            # 23456 찾기
            elif all(x in sorted_dice for x in [2, 3, 4, 5, 6]):
                target_dice = []
                temp_dice = my_dice.copy()
                
                for num in [2, 3, 4, 5, 6]:
                    if num in temp_dice:
                        target_dice.append(num)
                        temp_dice.remove(num)
                
                score = self.calculate_rule_potential_score(target_dice, rule)
                return (target_dice, score)
        
        elif rule == DiceRule.YACHT:
            # 5개 모두 같은 숫자 찾기
            for num in range(1, 7):
                count = my_dice.count(num)
                if count >= 5:
                    # 실제 보유한 해당 숫자들 중 5개 선택
                    target_dice = []
                    temp_dice = my_dice.copy()
                    
                    for i in range(5):
                        target_dice.append(num)
                        temp_dice.remove(num)
                    
                    score = self.calculate_rule_potential_score(target_dice, rule)
                    return (target_dice, score)
        
        # 규칙에 맞는 조합을 찾지 못한 경우, 기본 조합 사용
        dice = my_dice[:5] if len(my_dice) >= 5 else [0] * 5
        score = self.calculate_rule_potential_score(dice, rule)
        return (dice, score)

    # ============================== [필수 구현 끝] ==============================

    def update_get(
        self,
        dice_a: List[int],
        dice_b: List[int],
        my_bid: Bid,
        opp_bid: Bid,
        my_group: str,
    ):
        """입찰 결과를 받아서 상태 업데이트"""

        
        # 상대방의 입찰 가격 저장
        self.save_opponent_bid(self.current_round, opp_bid.amount)
        
        # 그룹에 따라 주사위 분배
        if my_group == "A":
            self.my_state.add_dice(dice_a)
            self.opp_state.add_dice(dice_b)
        else:
            self.my_state.add_dice(dice_b)
            self.opp_state.add_dice(dice_a)

        # 입찰 결과에 따른 점수 반영
        my_bid_ok = my_bid.group == my_group
        self.my_state.bid(my_bid_ok, my_bid.amount)

        opp_group = "B" if my_group == "A" else "A"
        opp_bid_ok = opp_bid.group == opp_group
        self.opp_state.bid(opp_bid_ok, opp_bid.amount)
        


    def update_put(self, put: DicePut):
        """내가 주사위를 배치한 결과 반영"""

        self.my_state.use_dice(put)
        # 내가 YACHT를 완성했는지 확인
        self.check_my_yacht_completion()


    def update_set(self, put: DicePut):
        """상대가 주사위를 배치한 결과 반영"""

        self.opp_state.use_dice(put)
        # 상대방이 YACHT를 완성했는지 확인
        self.check_opponent_yacht_completion()


def main():
    game = Game()

    # 입찰 라운드에서 나온 주사위들
    dice_a, dice_b = [0] * 5, [0] * 5
    # 내가 마지막으로 한 입찰 정보
    my_bid = Bid("", 0)

    while True:
        try:
            line = input().strip()
            if not line:
                continue

            command, *args = line.split()
    

            if command == "READY":
                # 게임 시작
        
                print("OK")
                continue

            if command == "ROLL":
                # 주사위 굴리기 결과 받기
                game.current_round += 1  # 턴 증가
                str_a, str_b = args
                for i, c in enumerate(str_a):
                    dice_a[i] = int(c)  # 문자를 숫자로 변환
                for i, c in enumerate(str_b):
                    dice_b[i] = int(c)  # 문자를 숫자로 변환
                
        
                my_bid = game.calculate_bid(dice_a, dice_b)
        
                print(f"BID {my_bid.group} {my_bid.amount}")
                continue

            if command == "GET":
                # 주사위 받기
                get_group, opp_group, opp_score = args
                opp_score = int(opp_score)
        
                game.update_get(
                    dice_a, dice_b, my_bid, Bid(opp_group, opp_score), get_group
                )
                continue

            if command == "SCORE":
                # 주사위 골라서 배치하기
        
                put = game.calculate_put()
                game.update_put(put)
                assert put.rule is not None
        
                print(f"PUT {put.rule.name} {''.join(map(str, put.dice))}")
                continue

            if command == "SET":
                # 상대의 주사위 배치
                rule, str_dice = args
                dice = [int(c) for c in str_dice]
        
                game.update_set(DicePut(DiceRule[rule], dice))
                continue

            if command == "FINISH":
                # 게임 종료
        
                break

            # 알 수 없는 명령어 처리
    
            print(f"Invalid command: {command}", file=sys.stderr)
            sys.exit(1)

        except EOFError:
    
            break
        except Exception as e:
    
            print(f"# Debug: Exception: {e}", file=sys.stderr)
            raise


if __name__ == "__main__":
    main()
